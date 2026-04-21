import React, { useEffect, useState } from 'react'
import AsyncSelect from 'react-select/async'
import DatePickerField from '../components/DatePickerField'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import { formatDate } from '../utils/dateTime'
import { notifyError, notifySuccess, notifyWarning } from '../services/notify'

const defaultLeaveForm = {
  employee: '',
  leave_type: 'sick',
  start_time: '',
  end_time: '',
  reason: ''
}

function getDatePart(dt){
  if(!dt) return ''
  return dt.slice(0,10)
}

function getTimePart(dt){
  if(!dt) return ''
  return dt.length >= 16 ? dt.slice(11,16) : ''
}

function toIsoString(value){
  if(!value) return ''
  const parsed = new Date(value)
  if(Number.isNaN(parsed.getTime())) return value
  return parsed.toISOString()
}

export default function LeaveManagement(){
  const [leaves, setLeaves] = useState([])
  const [pendingLeaves, setPendingLeaves] = useState([])
  const [employeeLeaves, setEmployeeLeaves] = useState([])
  const [employeeLookupId, setEmployeeLookupId] = useState('')
  const [view, setView] = useState('create') // 'create' | 'all' | 'employee'

  const [loading, setLoading] = useState(false)

  const [leaveForm, setLeaveForm] = useState(defaultLeaveForm)
  const { displayName, auth } = useAuth()
  const [selectedEmployeeOption, setSelectedEmployeeOption] = useState(null)
  const [selectedLookupOption, setSelectedLookupOption] = useState(null)

  useEffect(()=>{
    loadLeaves()
    loadPending()
  }, [])

  async function loadLeaves(){
    setLoading(true)
    try{
      const data = await api.getLeaves()
      const rows = data.results || data || []
      setLeaves(Array.isArray(rows) ? rows : [])
    }catch(requestError){
      notifyError(requestError.message || 'Unable to load leaves')
    }finally{
      setLoading(false)
    }
  }

  async function loadPending(){
    try{
      const data = await api.getPendingApprovals()
      const rows = data.leaves || data.results || []
      setPendingLeaves(Array.isArray(rows) ? rows : [])
    }catch(requestError){
      notifyError(requestError.message || 'Unable to load pending approvals')
    }
  }

  async function createLeave(event){
    event.preventDefault()
    try{
      await api.createLeave({
        ...leaveForm,
        start_time: toIsoString(leaveForm.start_time),
        end_time: toIsoString(leaveForm.end_time)
      })
      setLeaveForm(defaultLeaveForm)
      notifySuccess('Leave request submitted')
      await loadLeaves()
      await loadPending()
    }catch(requestError){
      notifyError(requestError.message || 'Unable to submit leave request')
    }
  }

  async function approveLeave(leaveId){
    try{
      await api.approveLeave(leaveId, { approved_by: displayName || 'Manager' })
      notifySuccess(`Leave ${leaveId} approved`)
      await loadLeaves()
      await loadPending()
    }catch(requestError){
      notifyError(requestError.message || 'Unable to approve leave')
    }
  }

  async function rejectLeave(leaveId){
    try{
      await api.rejectLeave(leaveId, { approved_by: displayName || 'Manager' })
      notifySuccess(`Leave ${leaveId} rejected`)
      await loadLeaves()
      await loadPending()
    }catch(requestError){
      notifyError(requestError.message || 'Unable to reject leave')
    }
  }

  async function lookupEmployeeLeaves(){
    if(!employeeLookupId){
      notifyWarning('Please select an employee first')
      return
    }
    try{
      const data = await api.getEmployeeLeaves({ emp_id: employeeLookupId })
      const rows = data.results || data || []
      setEmployeeLeaves(Array.isArray(rows) ? rows : [])
    }catch(requestError){
      notifyError(requestError.message || 'Unable to load employee leaves')
    }
  }

  return (
    <div className="page-stack">
      <div className="page-controls">
        <div className="view-tabs">
          <button className={view === 'create' ? 'btn primary' : 'btn secondary'} onClick={()=> setView('create')}>Create Leave</button>
          <button className={view === 'all' ? 'btn primary' : 'btn secondary'} onClick={()=> setView('all')}>All Leave Requests</button>
          <button className={view === 'employee' ? 'btn primary' : 'btn secondary'} onClick={()=> setView('employee')}>Employee Lookup</button>
        </div>
      </div>

      {view === 'create' && (
        <section className="surface split-grid">
          <article>
            <h2>Create Leave Request</h2>
            <form className="form-grid" onSubmit={createLeave}>
              <label>
                Employee
                <AsyncSelect
                  cacheOptions
                  defaultOptions
                  value={selectedEmployeeOption}
                  className="leave-employee-select"
                  classNamePrefix="rs"
                  loadOptions={async (inputValue) => {
                    try{
                      const data = await api.getEmployees({ search: inputValue, page_size: 20 })
                      const rows = data.results || data || []
                      return (Array.isArray(rows) ? rows : []).map(r => ({
                        label: `${r.name || r.employee_name || r.emp_id}` + (r.emp_id ? ` • ${r.emp_id}` : ''),
                        value: r.emp_id || r.id,
                        raw: r
                      }))
                    }catch(e){
                      return []
                    }
                  }}
                  onChange={(option)=>{
                    setSelectedEmployeeOption(option)
                    setLeaveForm({ ...leaveForm, employee: option ? option.value : '' })
                  }}
                  placeholder="Select employee..."
                />
              </label>

              <label>
                Leave Type
                <select
                  value={leaveForm.leave_type}
                  onChange={(event)=> setLeaveForm({ ...leaveForm, leave_type: event.target.value })}
                >
                  <option value="sick">sick</option>
                  <option value="casual">casual</option>
                  <option value="earned">earned</option>
                  <option value="unpaid">unpaid</option>
                  <option value="maternity">maternity</option>
                </select>
              </label>

              <label>
                Start Date & Time
                <div className="datetime-row">
                  <DatePickerField
                    value={getDatePart(leaveForm.start_time)}
                    required
                    onChange={(isoDate)=>{
                      const time = getTimePart(leaveForm.start_time) || '00:00'
                      setLeaveForm({ ...leaveForm, start_time: `${isoDate}T${time}` })
                    }}
                  />
                  <input
                    type="time"
                    value={getTimePart(leaveForm.start_time)}
                    required
                    onChange={(e)=>{
                      const time = e.target.value
                      const date = getDatePart(leaveForm.start_time) || new Date().toISOString().slice(0,10)
                      setLeaveForm({ ...leaveForm, start_time: `${date}T${time}` })
                    }}
                  />
                </div>
              </label>

              <label>
                End Date & Time
                <div className="datetime-row">
                  <DatePickerField
                    value={getDatePart(leaveForm.end_time)}
                    required
                    onChange={(isoDate)=>{
                      const time = getTimePart(leaveForm.end_time) || '00:00'
                      setLeaveForm({ ...leaveForm, end_time: `${isoDate}T${time}` })
                    }}
                  />
                  <input
                    type="time"
                    value={getTimePart(leaveForm.end_time)}
                    required
                    onChange={(e)=>{
                      const time = e.target.value
                      const date = getDatePart(leaveForm.end_time) || new Date().toISOString().slice(0,10)
                      setLeaveForm({ ...leaveForm, end_time: `${date}T${time}` })
                    }}
                  />
                </div>
              </label>

              <label className="full-width">
                Reason
                <textarea
                  rows="3"
                  value={leaveForm.reason}
                  onChange={(event)=> setLeaveForm({ ...leaveForm, reason: event.target.value })}
                ></textarea>
              </label>

              <div className="form-actions">
                <button className="btn primary" type="submit">Submit Leave</button>
              </div>
            </form>
          </article>

          {auth?.role !== 'manager' && (
            <article>
              <div className="section-heading">
                <h3>Pending Approvals</h3>
                <span>{pendingLeaves.length} open requests</span>
              </div>

              {/* Approver display removed from pending-approvals card to reduce visual clutter */}

              <div className="stacked-list">
                {pendingLeaves.length === 0 && <p className="empty-row">No pending leaves.</p>}
                {pendingLeaves.map((leave)=> (
                  <div key={leave.id} className="list-item">
                    <div>
                      <p><strong>{leave.employee}</strong> • {leave.employee_name ?? '-'} • {leave.leave_type}</p>
                      <small>{formatDate(leave.start_time)} to {formatDate(leave.end_time)}</small>
                    </div>
                    <div className="row-actions">
                      <button className="btn secondary" onClick={()=> approveLeave(leave.id)}>Approve</button>
                      <button className="btn icon danger" onClick={()=> rejectLeave(leave.id)}>
                        <i className="fa fa-times"></i>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </article>
          )}
        </section>
      )}

      {view === 'all' && (
        <section className="surface">
          <div className="section-heading">
            <h3>All Leave Requests</h3>
            <button className="btn secondary" onClick={loadLeaves} disabled={loading}>Refresh</button>
          </div>

          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Employee ID</th>
                  <th>Name</th>
                  <th>Reason</th>
                  <th>Start Date</th>
                  <th>End Date</th>
                  <th>Duration</th>
                  <th>Approved</th>
                  <th>Approved By</th>
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr>
                    <td colSpan="8" className="empty-row">Loading leave requests...</td>
                  </tr>
                )}

                {!loading && leaves.length === 0 && (
                  <tr>
                    <td colSpan="8" className="empty-row">No leave requests found.</td>
                  </tr>
                )}

                {!loading && leaves.map((leave)=> (
                  <tr key={leave.id}>
                    <td>{leave.employee ?? '-'}</td>
                    <td>{leave.employee_name ?? '-'}</td>
                    <td className="truncate-cell">{`${leave.leave_type || ''}${leave.reason ? ': ' + leave.reason : ''}` || '-'}</td>
                    <td>{formatDate(leave.start_time)}</td>
                    <td>{formatDate(leave.end_time)}</td>
                    <td>{leave.duration_days ?? leave.duration ?? '-'}</td>
                    <td>{leave.approved ? 'Yes' : 'No'}</td>
                    <td>{leave.approved_by || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {view === 'employee' && (
        <section className="surface">
          <div className="section-heading">
            <h3>Employee Leave History</h3>
            <span>Get leave records for one employee</span>
          </div>

          <div className="inline-form">
            <AsyncSelect
              cacheOptions
              defaultOptions
              value={selectedLookupOption}
              className="leave-employee-select"
              classNamePrefix="rs"
              loadOptions={async (inputValue) => {
                try{
                  const data = await api.getEmployees({ search: inputValue, page_size: 20 })
                  const rows = data.results || data || []
                  return (Array.isArray(rows) ? rows : []).map(r => ({
                    label: `${r.name || r.employee_name || r.emp_id}` + (r.emp_id ? ` • ${r.emp_id}` : ''),
                    value: r.emp_id || r.id,
                    raw: r
                  }))
                }catch(e){
                  return []
                }
              }}
              onChange={(option)=>{
                setSelectedLookupOption(option)
                setEmployeeLookupId(option ? option.value : '')
              }}
              placeholder="Select employee..."
            />
            <button className="btn secondary" onClick={lookupEmployeeLeaves}>Load History</button>
          </div>

          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Employee ID</th>
                  <th>Name</th>
                  <th>Reason</th>
                  <th>Start Date</th>
                  <th>End Date</th>
                  <th>Duration</th>
                  <th>Approved</th>
                  <th>Approved By</th>
                </tr>
              </thead>
              <tbody>
                {employeeLeaves.length === 0 && (
                  <tr>
                    <td colSpan="8" className="empty-row">No employee leave history loaded.</td>
                  </tr>
                )}
                {employeeLeaves.map((leave)=> (
                  <tr key={leave.id}>
                    <td>{leave.employee ?? employeeLookupId ?? '-'}</td>
                    <td>{leave.employee_name ?? '-'}</td>
                    <td className="truncate-cell">{`${leave.leave_type || ''}${leave.reason ? ': ' + leave.reason : ''}` || '-'}</td>
                    <td>{formatDate(leave.start_time)}</td>
                    <td>{formatDate(leave.end_time)}</td>
                    <td>{leave.duration_days ?? leave.duration ?? '-'}</td>
                    <td>{leave.approved ? 'Yes' : 'No'}</td>
                    <td>{leave.approved_by || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}
