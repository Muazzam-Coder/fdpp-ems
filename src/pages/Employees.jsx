import React, { useEffect, useMemo, useState, useRef, useTransition } from 'react'
import { useAuth } from '../context/AuthContext'
import PortalModal from '../components/PortalModal'
import api from '../services/api'
import { formatDateRangeText, formatTime12 } from '../utils/dateTime'
import DatePickerField from '../components/DatePickerField'
import Select from 'react-select'
import { notifyError, notifySuccess, notifyWarning } from '../services/notify'

const defaultForm = {
  emp_id: '',
  name: '',
  designation: '',
  profile_img: null,
  remove_image: false,
  salary: '',
  hourly_rate: '',
  shift_type: '',
  start_time: '',
  end_time: '',
  address: '',
  phone: '',
  CNIC: '',
  relative: '',
  r_phone: '',
  r_address: '',
  referance: '',
  relatives: [],
  status: 'active'
}

function toTimeInput(value){
  if(!value) return ''
  const parts = String(value).split(':')
  if(parts.length < 2) return value
  return `${parts[0]}:${parts[1]}`
}

function toApiTime(value){
  if(!value) return ''
  return value.length === 5 ? `${value}:00` : value
}

function toMinutes(value){
  if(!value) return null
  const parts = String(value).split(':')
  if(parts.length < 2) return null
  const hour = Number(parts[0])
  const minute = Number(parts[1])
  if(!Number.isFinite(hour) || !Number.isFinite(minute)) return null
  return hour * 60 + minute
}

function calculateHourlyRate(salary, startTime, endTime){
  const monthlySalary = Number(salary)
  const startMinutes = toMinutes(startTime)
  const endMinutes = toMinutes(endTime)


  if(!Number.isFinite(monthlySalary) || monthlySalary <= 0 || startMinutes === null || endMinutes === null){
    return ''
  }

  let minutes = endMinutes - startMinutes
  if(minutes <= 0) minutes += 24 * 60
  const totalHours = minutes / 60
  if(totalHours <= 0) return ''

  const oneDaySalary = monthlySalary / 30
  const hourlyRate = oneDaySalary / totalHours
  return hourlyRate.toFixed(2)
}

function formatPhone(value){
  if(value == null) return ''
  // Limit to 11 digits (excluding hyphen). Format as XXXX-XXXXXXX
  const digits = String(value).replace(/\D/g, '').slice(0, 11)
  if(digits.length <= 4) return digits
  const first = digits.slice(0,4)
  const rest = digits.slice(4)
  return rest ? `${first}-${rest}` : first
}

function formatCNIC(value){
  if(value == null) return ''
  const digits = String(value).replace(/\D/g, '')
  const p1 = digits.slice(0,5)
  const p2 = digits.length > 5 ? digits.slice(5,12) : ''
  const p3 = digits.length > 12 ? digits.slice(12,13) : ''
  const parts = []
  if(p1) parts.push(p1)
  if(p2) parts.push(p2)
  if(p3) parts.push(p3)
  return parts.join('-')
}

// ------ Form helpers ------
/** Normalize different relatives input shapes into array of string IDs. */
function normalizeRelativesInput(value){
  if(!value) return []
  if(Array.isArray(value)){
    return value.map(item => {
      if(item && typeof item === 'object'){
        return String(item.emp_id ?? item.id ?? item)
      }
      return String(item)
    }).filter(Boolean)
  }
  if(typeof value === 'number') return [String(value)]
  if(typeof value === 'string'){
    const trimmed = value.trim()
    if(!trimmed) return []
    try{
      const parsed = JSON.parse(trimmed)
      if(Array.isArray(parsed)) return parsed.map(it => String(it)).filter(Boolean)
      if(parsed) return [String(parsed)]
    }catch(_){}
    // fallback CSV
    return trimmed.split(',').map(s => s.trim()).filter(Boolean)
  }
  return []
}

/** Append each relative ID as a repeated 'relatives' field in FormData. */
function appendRelativesToFormData(formData, relativesArray){
  if(!Array.isArray(relativesArray)) return
  for(const id of relativesArray){
    if(id != null) formData.append('relatives', String(id))
  }
}

export default function Employees(){
  const { auth } = useAuth()
  const [employees, setEmployees] = useState([])
  const [totalCount, setTotalCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [statusFilter, setStatusFilter] = useState('all')
  const [shiftFilter, setShiftFilter] = useState('all')
  // immediate input value for name (debounced)
  const [employeeNameInput, setEmployeeNameInput] = useState('')
  // debounced filter value used to trigger load
  const [employeeNameFilter, setEmployeeNameFilter] = useState('')
  // immediate input value for employee id (debounced)
  const [employeeIdInput, setEmployeeIdInput] = useState('')
  // debounced filter value used to trigger load
  const [employeeIdFilter, setEmployeeIdFilter] = useState('')

  const [showForm, setShowForm] = useState(false)
  const [editingEmployee, setEditingEmployee] = useState(null)
  const [form, setForm] = useState(defaultForm)
  const [submitting, setSubmitting] = useState(false)

  const [reportForm, setReportForm] = useState({ emp_id: '', period: 'month', start_date: '', end_date: '' })
  const [attendanceReport, setAttendanceReport] = useState(null)
  const [reportError, setReportError] = useState('')
  const [reportLoading, setReportLoading] = useState(false)

  const [payoutModal, setPayoutModal] = useState({ open: false, employee: null })
  const [payoutRange, setPayoutRange] = useState({ start_date: '', end_date: '' })
  const [payoutResult, setPayoutResult] = useState(null)
  const [payoutError, setPayoutError] = useState('')
  const [payoutLoading, setPayoutLoading] = useState(false)

  const [shiftOptions, setShiftOptions] = useState([])

  const [isPending, startTransition] = useTransition()

  const relativeOptions = useMemo(() => {
    const excludeId = editingEmployee ? String(editingEmployee.emp_id ?? editingEmployee.id ?? '') : ''
    return employees
      .filter(emp => String(emp.emp_id ?? emp.id) !== excludeId)
      .map(emp => ({
        value: String(emp.emp_id ?? emp.id),
        label: emp.name || emp.username || String(emp.emp_id ?? emp.id)
      }))
  }, [employees, editingEmployee])

  const selectedRelatives = useMemo(() => {
    if(!Array.isArray(form.relatives)) return []
    return relativeOptions.filter(opt => form.relatives.includes(opt.value))
  }, [form.relatives, relativeOptions])

  function handleRelativesChange(selected){
    const ids = Array.isArray(selected) ? selected.map(s => s.value) : []
    setForm(prev => ({ ...prev, relatives: ids }))
  }

  const fileInputRef = useRef(null)
  const [previewUrl, setPreviewUrl] = useState('')

  useEffect(()=>{
    // create preview URL when a File is selected
    if(form.profile_img && form.profile_img instanceof File){
      const url = URL.createObjectURL(form.profile_img)
      setPreviewUrl(url)
      return ()=> URL.revokeObjectURL(url)
    }
    // if profile_img is a string (existing URL), use it
    if(form.profile_img && typeof form.profile_img === 'string'){
      setPreviewUrl(form.profile_img)
      return
    }
    setPreviewUrl('')
  }, [form.profile_img])

  function handleAvatarClick(){
    if(fileInputRef.current) fileInputRef.current.click()
  }

  function handleFileChange(event){
    const file = event.target.files && event.target.files[0] ? event.target.files[0] : null
    setForm(prev => ({ ...prev, profile_img: file, remove_image: false }))
  }

  function handleDropAvatar(event){
    event.preventDefault()
    const file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0] ? event.dataTransfer.files[0] : null
    if(file) setForm(prev => ({ ...prev, profile_img: file, remove_image: false }))
  }

  function handleDragOver(event){
    event.preventDefault()
  }

  function handleRemoveImage(){
    // Clear selected file and mark removal for backend
    setForm(prev => ({ ...prev, profile_img: null, remove_image: true }))
    setPreviewUrl('')
  }

  useEffect(()=>{
    loadEmployees()
  }, [statusFilter, shiftFilter, employeeIdFilter, employeeNameFilter])

  // debounce employeeNameInput -> employeeNameFilter
  useEffect(()=>{
    const t = setTimeout(()=> startTransition(()=> setEmployeeNameFilter(String(employeeNameInput || '').trim())), 450)
    return ()=> clearTimeout(t)
  }, [employeeNameInput])

  // debounce employeeIdInput -> employeeIdFilter
  useEffect(()=>{
    const t = setTimeout(()=> startTransition(()=> setEmployeeIdFilter(String(employeeIdInput || '').trim())), 450)
    return ()=> clearTimeout(t)
  }, [employeeIdInput])

  useEffect(()=>{
    async function loadShifts(){
      try{
        const data = await api.getShifts()
        const rows = data.results || data || []
        setShiftOptions(Array.isArray(rows) ? rows : [])
      }catch(err){
        console.warn('Unable to load shifts', err)
      }
    }
    loadShifts()
  }, [])

  useEffect(()=>{
    const computed = calculateHourlyRate(form.salary, form.start_time, form.end_time)
    setForm((prev)=>{
      if(prev.hourly_rate === computed) return prev
      return { ...prev, hourly_rate: computed }
    })
  }, [form.salary, form.start_time, form.end_time])

  useEffect(()=>{
    if(error) notifyError(error)
  }, [error])

  useEffect(()=>{
    if(reportError) notifyError(reportError)
  }, [reportError])

  useEffect(()=>{
    if(payoutError) notifyError(payoutError)
  }, [payoutError])

  const statuses = useMemo(()=> ['all', 'active', 'inactive'], [])
  const shiftNames = useMemo(() => [ 'all', ...shiftOptions.map(s => s.name || s.id) ], [shiftOptions])

  function getInitials(u){
    const name = (u.name || u.username || '').trim()
    if(!name) return '?'
    const parts = name.split(/\s+/).filter(Boolean)
    if(parts.length === 1) return parts[0].slice(0,2).toUpperCase()
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }

  async function loadEmployees(){
    setLoading(true)
    setError('')
    const params = {}
    if(statusFilter !== 'all') params.status = statusFilter
    if(shiftFilter !== 'all') params.shift_type = shiftFilter
    if(employeeIdFilter) params.employee_id = String(employeeIdFilter).trim()
    if(employeeNameFilter) params.employee_name = String(employeeNameFilter).trim()

    try{
      const data = await api.getEmployees(params)
      const rows = data.results || data || []
      setEmployees(Array.isArray(rows) ? rows : [])
      setTotalCount(data.count || (Array.isArray(rows) ? rows.length : 0))
    }catch(requestError){
      setError(requestError.message || 'Unable to load employees')
    }finally{
      setLoading(false)
    }
  }

  function openCreate(){
    setEditingEmployee(null)
    setForm(defaultForm)
    setShowForm(true)
  }

  function openEdit(employee){
    setEditingEmployee(employee)
    setForm({
      emp_id: employee.emp_id || '',
      name: employee.name || '',
      designation: employee.designation || '',
      profile_img: employee.profile_img || null,
      remove_image: false,
      salary: employee.salary || '',
      hourly_rate: employee.hourly_rate || '',
      shift_type: employee.shift_type || '',
      start_time: toTimeInput(employee.start_time),
      end_time: toTimeInput(employee.end_time),
      address: employee.address || '',
      phone: formatPhone(employee.phone || ''),
      CNIC: formatCNIC(employee.CNIC || ''),
      relative: employee.relative || '',
      r_phone: formatPhone(employee.r_phone || ''),
      r_address: employee.r_address || '',
      referance: employee.referance || '',
      relatives: normalizeRelativesInput(employee.relatives).filter(id => id !== String(employee.emp_id ?? employee.id ?? '')),
      status: employee.status || 'active'
    })
    setShowForm(true)
  }

  async function saveEmployee(event){
    event.preventDefault()
    setSubmitting(true)
    setError('')

    // Build FormData so profile image can be uploaded as binary.
    const formData = new FormData()
    // Append scalar fields
    formData.append('name', form.name || '')
    formData.append('designation', form.designation || '')
    if(form.emp_id) formData.append('emp_id', String(form.emp_id))
    formData.append('salary', String(form.salary || ''))
    formData.append('hourly_rate', String(form.hourly_rate || ''))
    formData.append('shift_type', form.shift_type || '')
    formData.append('start_time', toApiTime(form.start_time) || '')
    formData.append('end_time', toApiTime(form.end_time) || '')
    formData.append('address', form.address || '')
    formData.append('phone', form.phone ? String(form.phone).replace(/\D/g, '') : '')
    formData.append('CNIC', form.CNIC ? String(form.CNIC).replace(/\D/g, '') : '')
    formData.append('relative', form.relative || '')
    formData.append('r_phone', form.r_phone ? String(form.r_phone).replace(/\D/g, '') : '')
    formData.append('r_address', form.r_address || '')
    formData.append('referance', form.referance || '')
    const relativesList = normalizeRelativesInput(form.relatives)
    appendRelativesToFormData(formData, relativesList)
    formData.append('status', form.status || 'active')

    // Only append file if user selected one (File object). If editing and leaving empty, backend should preserve existing image.
    if(form.profile_img && form.profile_img instanceof File){
      formData.append('profile_img', form.profile_img)
    }

    // If user removed the image explicitly, include a flag so backend can clear it
    if(form.remove_image){
      formData.append('profile_img', '')
      formData.append('remove_profile_img', '1')
    }

    try{
      if(editingEmployee){
        await api.updateEmployee(editingEmployee.emp_id, formData)
        notifySuccess('Employee updated successfully')
      }else{
        await api.createEmployee(formData)
        notifySuccess('Employee created successfully')
      }
      setShowForm(false)
      await loadEmployees()
    }catch(requestError){
      setError(requestError.message || 'Unable to save employee')
    }finally{
      setSubmitting(false)
    }
  }

  async function removeEmployee(employee){
    const allow = window.confirm(`Delete employee ${employee.emp_id}?`)
    if(!allow) return
    try{
      await api.deleteEmployee(employee.emp_id)
      notifySuccess('Employee deleted successfully')
      await loadEmployees()
    }catch(requestError){
      setError(requestError.message || 'Unable to delete employee')
    }
  }

  async function fetchAttendanceReport(event){
    event.preventDefault()
    if(!reportForm.emp_id){
      notifyWarning('Employee ID is required for attendance report')
      return
    }

    setReportLoading(true)
    setReportError('')
    setAttendanceReport(null)

    const params = { period: reportForm.period }
    if(reportForm.start_date) params.start_date = reportForm.start_date
    if(reportForm.end_date) params.end_date = reportForm.end_date

    try{
      const data = await api.getEmployeeAttendanceReport(reportForm.emp_id, params)
      setAttendanceReport(data)
    }catch(requestError){
      setReportError(requestError.message || 'Unable to fetch attendance report')
    }finally{
      setReportLoading(false)
    }
  }

  function openPayout(employee){
    const today = new Date()
    const firstDay = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-01`
    const currentDay = today.toISOString().split('T')[0]
    setPayoutRange({ start_date: firstDay, end_date: currentDay })
    setPayoutResult(null)
    setPayoutError('')
    setPayoutModal({ open: true, employee })
  }

  async function calculatePayout(event){
    event.preventDefault()
    if(!payoutModal.employee) return
    setPayoutLoading(true)
    setPayoutError('')
    setPayoutResult(null)
    try{
      const data = await api.calculatePayout(payoutModal.employee.emp_id, payoutRange)
      setPayoutResult(data)
    }catch(requestError){
      setPayoutError(requestError.message || 'Unable to calculate payout')
    }finally{
      setPayoutLoading(false)
    }
  }

  // lock body scroll when modals are open
  useEffect(() => {
    const originalOverflow = document.body.style.overflow
    if (showForm || payoutModal.open) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = originalOverflow
    }
    return () => { document.body.style.overflow = originalOverflow }
  }, [showForm, payoutModal.open])

  const inputBase = 'w-full px-3 py-2 border rounded-lg text-sm transition duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-teal-100 focus:border-teal-500'
  const labelBase = 'flex flex-col gap-1 text-sm text-gray-700'
  const primaryBtn = 'inline-flex items-center justify-center rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white transition duration-150 ease-in-out hover:shadow-sm'
  const secondaryBtn = 'inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition duration-150 ease-in-out hover:shadow-sm'

  return (
    <div className="space-y-4" style={{ animation: 'rise 0.45s ease both' }}>
      <section className="bg-white border border-gray-200 rounded-xl p-4">
          <div className="mb-3">
            <h3 className="text-lg font-semibold">Attendance Status</h3>
          </div>

          <form className="flex flex-wrap items-center gap-3" onSubmit={fetchAttendanceReport}>
            <input
              className={inputBase}
              placeholder="Employee ID"
              value={reportForm.emp_id}
              onChange={(event)=> setReportForm({ ...reportForm, emp_id: event.target.value })}
            />

            <select className={inputBase + ' max-w-[140px]'} value={reportForm.period} onChange={(event)=> setReportForm({ ...reportForm, period: event.target.value })}>
              <option value="day">day</option>
              <option value="week">week</option>
              <option value="month">month</option>
            </select>

            <div className="w-40">
              <DatePickerField
                value={reportForm.start_date}
                onChange={(value)=> setReportForm({ ...reportForm, start_date: value })}
              />
            </div>

            <div className="w-40">
              <DatePickerField
                value={reportForm.end_date}
                onChange={(value)=> setReportForm({ ...reportForm, end_date: value })}
              />
            </div>

            <button className={secondaryBtn} type="submit" disabled={reportLoading}>
              {reportLoading ? 'Loading...' : 'Load Report'}
            </button>
          </form>

        {attendanceReport && (
          <div className="report-grid">
            <article>
              <p>Employee</p>
              <h4>{attendanceReport.employee_name}</h4>
              <small>{attendanceReport.employee_id}</small>
            </article>
            <article>
              <p>Total Days Worked</p>
              <h4>{attendanceReport.total_days_worked || 0}</h4>
              <small>{formatDateRangeText(attendanceReport.period)}</small>
            </article>
            <article>
              <p>Total Hours</p>
              <h4>{attendanceReport.total_hours || 0}</h4>
              <small>On Time: {attendanceReport.on_time || 0}</small>
            </article>
            <article>
              <p>Late Count</p>
              <h4>{attendanceReport.late || 0}</h4>
              <small>Records: {(attendanceReport.attendance_records || []).length}</small>
            </article>
          </div>
        )}
      </section>

      <section className="bg-white border border-gray-200 rounded-xl p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center">
            <h2 className="text-lg font-semibold">Employee List</h2>
            {isPending && (
              <span className="ml-2 inline-block h-2 w-2 rounded-full bg-teal-600 animate-pulse" aria-hidden="true"></span>
            )}
          </div>
          <span className="text-sm text-gray-600">{totalCount} records</span>
        </div>

        <div className={`grid grid-cols-1 md:grid-cols-5 gap-3 items-center mb-4 ${loading ? 'opacity-85' : ''}`}>
          <label className={labelBase}>
            Employee ID
            <input
              className={inputBase}
              placeholder="ID"
              inputMode="numeric"
              pattern="[0-9]*"
              value={employeeIdInput}
              onChange={(e)=> setEmployeeIdInput(String(e.target.value || '').replace(/\D/g, ''))}
            />
          </label>

          <label className={labelBase}>
            Name
            <input className={inputBase} placeholder="Employee name" value={employeeNameInput} onChange={(e)=> setEmployeeNameInput(e.target.value)} />
          </label>

          <label className={labelBase}>
            Status
            <select className={inputBase} value={statusFilter} onChange={(event)=> startTransition(()=> setStatusFilter(event.target.value))}>
              {statuses.map((status)=> <option key={status} value={status}>{status}</option>)}
            </select>
          </label>

          <label className={labelBase}>
            Shift
            <select className={inputBase} value={shiftFilter} onChange={(event)=> startTransition(()=> setShiftFilter(event.target.value))}>
              {shiftNames.map((shift)=> <option key={shift} value={shift}>{shift}</option>)}
            </select>
          </label>

          <div className="flex items-center justify-end gap-2">
            <button className={secondaryBtn} onClick={loadEmployees} disabled={loading}>Refresh</button>
            <button className={primaryBtn} onClick={openCreate}>Add Employee</button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full table-auto">
            <thead>
              <tr>
                <th className="text-left text-xs font-semibold text-gray-600 uppercase tracking-wider px-4 py-2">ID</th>
                <th className="text-left text-xs font-semibold text-gray-600 uppercase tracking-wider px-4 py-2">Name</th>
                <th className="text-left text-xs font-semibold text-gray-600 uppercase tracking-wider px-4 py-2">Shift</th>
                <th className="text-left text-xs font-semibold text-gray-600 uppercase tracking-wider px-4 py-2">Timing</th>
                <th className="text-left text-xs font-semibold text-gray-600 uppercase tracking-wider px-4 py-2">Status</th>
                <th className="text-left text-xs font-semibold text-gray-600 uppercase tracking-wider px-4 py-2">Hourly Rate</th>
                <th className="text-left text-xs font-semibold text-gray-600 uppercase tracking-wider px-4 py-2">Hours Today</th>
                <th className="text-left text-xs font-semibold text-gray-600 uppercase tracking-wider px-4 py-2">Actions</th>
              </tr>
            </thead>
            <tbody className={loading ? 'opacity-40 transition-opacity duration-200' : 'transition-opacity duration-200'}>
              {!loading && employees.length === 0 && (
                <tr>
                  <td colSpan="8" className="text-center text-gray-500 p-4">No employee found for current filters.</td>
                </tr>
              )}

              {!loading && employees.map((employee)=> (
                <tr key={employee.emp_id} className="transition-colors duration-150 ease-in-out hover:bg-gray-50 odd:bg-white even:bg-gray-50">
                  <td className="px-4 py-3">{employee.emp_id}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3 min-w-0">
                      {employee.profile_img ? (
                        <img className="w-9 h-9 rounded-full object-cover" src={employee.profile_img} alt={employee.name || 'avatar'} />
                      ) : (
                        <div className="w-9 h-9 rounded-full bg-gray-200 flex items-center justify-center text-sm font-semibold text-gray-700">{getInitials(employee)}</div>
                      )}
                      <div className="min-w-0">
                        <div className="font-semibold truncate">{employee.name || '-'}</div>
                        <div className="text-sm text-gray-500 truncate">{employee.username || ''}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">{employee.shift_type || '-'}</td>
                  <td className="px-4 py-3">{formatTime12(employee.start_time)} - {formatTime12(employee.end_time)}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center justify-center rounded-full text-xs font-semibold px-2 py-1 ${employee.status === 'active' ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'}`}>
                      {employee.status || 'unknown'}
                    </span>
                  </td>
                  <td className="px-4 py-3">{employee.hourly_rate || '-'}</td>
                  <td className="px-4 py-3">{employee.total_hours_today || 0}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {auth?.role !== 'manager' ? (
                        <button className="p-2 rounded-md bg-white border hover:bg-gray-100" onClick={()=> openEdit(employee)} title="Edit employee">
                          <i className="fa fa-pen text-sm text-gray-700"></i>
                        </button>
                      ) : null}

                      <button className="p-2 rounded-md bg-white border hover:bg-gray-100" onClick={()=> openPayout(employee)} title="Calculate payout">
                        <i className="fa fa-coins text-sm text-gray-700"></i>
                      </button>

                      {auth?.role !== 'manager' ? (
                        <button className="p-2 rounded-md bg-red-50 hover:bg-red-100 text-red-600" onClick={()=> removeEmployee(employee)} title="Delete employee">
                          <i className="fa fa-trash text-sm"></i>
                        </button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {/* Skeleton overlay: covers table while loading to provide smooth transition */}
          <div className={`absolute inset-0 z-20 pointer-events-none transition-opacity duration-200 ${loading ? 'opacity-100' : 'opacity-0'}`} aria-hidden={!loading}>
            <div className="w-full h-full overflow-auto">
              <table className="min-w-full table-auto">
                <thead>
                  <tr>
                    <th className="px-4 py-2"><div className="skeleton-line skeleton h-4 w-16 rounded"></div></th>
                    <th className="px-4 py-2"><div className="skeleton-line skeleton h-4 w-36 rounded"></div></th>
                    <th className="px-4 py-2"><div className="skeleton-line skeleton h-4 w-20 rounded"></div></th>
                    <th className="px-4 py-2"><div className="skeleton-line skeleton h-4 w-40 rounded"></div></th>
                    <th className="px-4 py-2"><div className="skeleton-line skeleton h-4 w-20 rounded"></div></th>
                    <th className="px-4 py-2"><div className="skeleton-line skeleton h-4 w-20 rounded"></div></th>
                    <th className="px-4 py-2"><div className="skeleton-line skeleton h-4 w-12 rounded"></div></th>
                    <th className="px-4 py-2"><div className="skeleton-line skeleton h-4 w-24 rounded"></div></th>
                  </tr>
                </thead>
                <tbody>
                  {Array.from({ length: 6 }).map((_, i) => (
                    <tr key={`overlay-skel-${i}`} className="odd:bg-white even:bg-gray-50">
                      <td className="px-4 py-3"><div className="skeleton skeleton-avatar w-9 h-9"></div></td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="skeleton w-9 h-9 rounded-full"></div>
                          <div className="min-w-0">
                            <div className="skeleton-line skeleton h-4 w-32 mb-2"></div>
                            <div className="skeleton-line skeleton h-3 w-20"></div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3"><div className="skeleton-line skeleton h-4 w-12"></div></td>
                      <td className="px-4 py-3"><div className="skeleton-line skeleton h-4 w-28"></div></td>
                      <td className="px-4 py-3"><div className="skeleton-line skeleton h-4 w-16"></div></td>
                      <td className="px-4 py-3"><div className="skeleton-line skeleton h-4 w-12"></div></td>
                      <td className="px-4 py-3"><div className="skeleton-line skeleton h-4 w-8"></div></td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="skeleton-line skeleton h-8 w-8 rounded"></div>
                          <div className="skeleton-line skeleton h-8 w-8 rounded"></div>
                          <div className="skeleton-line skeleton h-8 w-8 rounded"></div>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <PortalModal
        open={showForm}
        onClose={() => setShowForm(false)}
        overlayClassName="fixed inset-0 z-[70] flex items-start sm:items-center justify-center bg-slate-900/60 p-2 md:p-4 backdrop-blur-sm overflow-y-auto"
        innerClassName="w-full flex items-center justify-center px-4 md:px-0"
      >
        <div className="w-full max-w-full sm:max-w-4xl mx-2 sm:mx-auto bg-white rounded-lg shadow-lg p-6 max-h-[90vh] overflow-auto relative">
            <div className="flex items-start justify-between mb-4">
              <h3 className="text-lg font-semibold">{editingEmployee ? `Edit ${editingEmployee.emp_id}` : 'Create Employee'}</h3>
              <button type="button" onClick={() => setShowForm(false)} className="text-gray-500 hover:text-gray-700">
                <i className="fa fa-times"></i>
              </button>
            </div>

            {submitting && (
              <div className="absolute inset-0 z-10 bg-white/70 p-6 flex flex-col gap-3">
                <div className="skeleton h-6 w-40 rounded"></div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="skeleton h-10 w-full rounded"></div>
                  <div className="skeleton h-10 w-full rounded"></div>
                  <div className="skeleton h-10 w-full rounded"></div>
                  <div className="skeleton h-10 w-full rounded"></div>
                </div>
                <div className="skeleton h-10 w-32 rounded mt-2"></div>
              </div>
            )}

            <form className="grid grid-cols-1 md:grid-cols-2 gap-4" onSubmit={saveEmployee}>
              <div className="col-span-1 md:col-span-2 flex items-center gap-4">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={handleFileChange}
                />

                <div className="relative">
                  <div
                    className="w-28 h-28 rounded-lg border border-gray-200 flex items-center justify-center bg-gray-50 cursor-pointer overflow-hidden"
                    onClick={handleAvatarClick}
                    onDrop={handleDropAvatar}
                    onDragOver={handleDragOver}
                    role="button"
                    tabIndex={0}
                  >
                    {previewUrl ? (
                      <img src={previewUrl} alt="avatar preview" className="w-full h-full object-cover" />
                    ) : (
                      <div className="flex flex-col items-center justify-center text-gray-400">
                        <i className="fa fa-cloud-upload-alt text-2xl"></i>
                        <span className="text-xs">Click or drop</span>
                      </div>
                    )}
                  </div>
                  {previewUrl && (
                    <button type="button" onClick={handleRemoveImage} className="absolute -right-2 -top-2 bg-red-50 text-red-600 rounded-full p-1 border border-red-100">
                      <i className="fa fa-trash text-xs"></i>
                    </button>
                  )}
                </div>

                <div className="flex-1">
                  {editingEmployee ? (
                    <label className={labelBase}>
                      Employee ID
                      <input value={form.emp_id} readOnly className={inputBase + ' bg-gray-100'} />
                    </label>
                  ) : null}
                  <p className="text-sm font-semibold mt-2">Personal Details</p>
                </div>
              </div>

              <label className={labelBase}>
                Name
                <input required value={form.name} onChange={(event)=> setForm({ ...form, name: event.target.value })} className={inputBase} />
              </label>


              <label className={labelBase}>
                Phone
                <input
                  value={form.phone}
                  onChange={(event)=> setForm({ ...form, phone: formatPhone(event.target.value) })}
                  className={inputBase}
                  inputMode="numeric"
                  maxLength={12}
                />
              </label>

              <label className={labelBase}>
                CNIC
                <input value={form.CNIC} onChange={(event)=> setForm({ ...form, CNIC: formatCNIC(event.target.value) })} className={inputBase} />
              </label>

              <label className={labelBase + ' md:col-span-2'}>
                Address
                <input value={form.address} onChange={(event)=> setForm({ ...form, address: event.target.value })} className={inputBase} />
              </label>

              <p className="text-sm font-semibold md:col-span-2 mt-2">Work Details</p>

              <label className={labelBase}>
                Shift Type
                <select
                  value={form.shift_type}
                  onChange={(event)=>{const val = event.target.value; const selected = shiftOptions.find(s => s.name === val || String(s.id) === val); setForm(prev => ({...prev, shift_type: val, start_time: selected ? toTimeInput(selected.start_time) : prev.start_time, end_time: selected ? toTimeInput(selected.end_time) : prev.end_time }))}}
                  className={inputBase}
                >
                  <option value="">-- select shift --</option>
                  {shiftOptions.map((s)=> <option key={s.id} value={s.name}>{s.name}</option>)}
                </select>
              </label>

              <label className={labelBase}>
                Designation
                <input value={form.designation} onChange={(event)=> setForm({ ...form, designation: event.target.value })} className={inputBase} />
              </label>

              <label className={labelBase}>
                Start Time
                <input type="time" required value={form.start_time} onChange={(event)=> setForm({ ...form, start_time: event.target.value })} className={inputBase} />
              </label>

              <label className={labelBase}>
                End Time
                <input type="time" required value={form.end_time} onChange={(event)=> setForm({ ...form, end_time: event.target.value })} className={inputBase} />
              </label>

              <label className={labelBase}>
                Salary
                <input type="number" step="0.01" required value={form.salary} onChange={(event)=> setForm({ ...form, salary: event.target.value })} className={inputBase} />
              </label>

              <label className={labelBase}>
                Hourly Rate (auto)
                <input type="text" value={form.hourly_rate} readOnly className={inputBase + ' bg-gray-100'} />
              </label>

              <label className={labelBase}>
                Status
                <select value={form.status} onChange={(event)=> setForm({ ...form, status: event.target.value })} className={inputBase}>
                  <option value="active">active</option>
                  <option value="inactive">inactive</option>
                </select>
              </label>

              <p className="text-sm font-semibold md:col-span-2 mt-2">Emergency Contact</p>

              <label className={labelBase}>
                Name
                <input value={form.relative} onChange={(event)=> setForm({ ...form, relative: event.target.value })} className={inputBase} />
              </label>

              <label className={labelBase}>
                Phone
                <input
                  value={form.r_phone}
                  onChange={(event)=> setForm({ ...form, r_phone: formatPhone(event.target.value) })}
                  className={inputBase}
                  inputMode="numeric"
                  maxLength={12}
                />
              </label>

              <label className={labelBase + ' md:col-span-2'}>
                Address
                <input value={form.r_address} onChange={(event)=> setForm({ ...form, r_address: event.target.value })} className={inputBase} />
              </label>

              <label className={labelBase}>
                Reference
                <input value={form.referance} onChange={(event)=> setForm({ ...form, referance: event.target.value })} className={inputBase} />
              </label>

              <label className={labelBase + ' md:col-span-2'}>
                Relatives
                <div className="w-full">
                  <Select
                    isMulti
                    isSearchable
                    backspaceRemovesValue={false}
                    options={relativeOptions}
                    value={selectedRelatives}
                    onChange={handleRelativesChange}
                    classNamePrefix="react-select"
                    placeholder="Search and select relatives..."
                  />
                </div>
                {/* <small className="text-xs text-gray-500">Select one or more employees</small> */}
              </label>

              <div className="col-span-1 md:col-span-2 flex justify-end gap-3 mt-2">
                <button type="button" className={secondaryBtn} onClick={()=> setShowForm(false)}>Cancel</button>
                <button type="submit" className={primaryBtn} disabled={submitting}>
                  {submitting ? 'Saving...' : 'Save Employee'}
                </button>
              </div>
            </form>
          </div>
        </PortalModal>

      <PortalModal
        open={payoutModal.open}
        onClose={() => setPayoutModal({ open: false, employee: null })}
        overlayClassName="fixed inset-0 z-[70] flex items-start sm:items-center justify-center bg-slate-900/60 p-2 md:p-4 backdrop-blur-sm overflow-y-auto"
        innerClassName="w-full flex items-center justify-center px-4 md:px-0"
      >
        <div className="w-full max-w-md mx-auto bg-white rounded-lg shadow-lg p-6 max-h-[90vh] overflow-auto relative">
            <div className="flex items-start justify-between mb-4">
              <h3 className="text-lg font-semibold">Payout for {payoutModal.employee?.name}</h3>
              <button type="button" onClick={()=> setPayoutModal({ open: false, employee: null })} className="text-gray-500 hover:text-gray-700">
                <i className="fa fa-times"></i>
              </button>
            </div>

            <form className="flex items-center gap-2 mb-4" onSubmit={calculatePayout}>
              <div className="w-40">
                <DatePickerField
                  value={payoutRange.start_date}
                  onChange={(value)=> setPayoutRange({ ...payoutRange, start_date: value })}
                  required
                />
              </div>
              <div className="w-40">
                <DatePickerField
                  value={payoutRange.end_date}
                  onChange={(value)=> setPayoutRange({ ...payoutRange, end_date: value })}
                  required
                />
              </div>
              <button className={primaryBtn} type="submit" disabled={payoutLoading}>
                {payoutLoading ? 'Calculating...' : 'Calculate'}
              </button>
            </form>

            {payoutResult && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <article className="p-3 bg-gray-50 rounded">
                  <p className="text-sm text-gray-600">Period</p>
                  <h4 className="font-semibold">{formatDateRangeText(payoutResult.period)}</h4>
                  <small className="text-sm text-gray-500">{payoutResult.employee_id}</small>
                </article>
                <article className="p-3 bg-gray-50 rounded">
                  <p className="text-sm text-gray-600">Total Hours</p>
                  <h4 className="font-semibold">{payoutResult.total_hours}</h4>
                  <small className="text-sm text-gray-500">Overtime: {payoutResult.overtime_hours}</small>
                </article>
                <article className="p-3 bg-gray-50 rounded">
                  <p className="text-sm text-gray-600">Base Payout</p>
                  <h4 className="font-semibold">{payoutResult.base_payout}</h4>
                  <small className="text-sm text-gray-500">Rate: {payoutResult.hourly_rate}</small>
                </article>
                <article className="p-3 bg-gray-50 rounded">
                  <p className="text-sm text-gray-600">Total Payout</p>
                  <h4 className="font-semibold">{payoutResult.total_payout}</h4>
                  <small className="text-sm text-gray-500">Overtime amount: {payoutResult.overtime_payout}</small>
                </article>
              </div>
            )}
          </div>
        </PortalModal>
    </div>
  )
}
