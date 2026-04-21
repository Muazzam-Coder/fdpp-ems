import React, { useEffect, useState } from 'react'
import AsyncSelect from 'react-select/async'
import api from '../services/api'
import { formatDate, formatDateTime, formatTime12 } from '../utils/dateTime'
import DatePickerField from '../components/DatePickerField'
import { notifyError } from '../services/notify'

const TODAY_ISO = new Date().toISOString().split('T')[0]
const NOW = new Date()
const CURRENT_MONTH = String(NOW.getMonth() + 1)
const CURRENT_YEAR = String(NOW.getFullYear())

const MONTH_OPTIONS = [
  { value: '1', label: 'January' },
  { value: '2', label: 'February' },
  { value: '3', label: 'March' },
  { value: '4', label: 'April' },
  { value: '5', label: 'May' },
  { value: '6', label: 'June' },
  { value: '7', label: 'July' },
  { value: '8', label: 'August' },
  { value: '9', label: 'September' },
  { value: '10', label: 'October' },
  { value: '11', label: 'November' },
  { value: '12', label: 'December' }
]

function statusLabel(value){
  if(!value) return 'N/A'
  return String(value)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function statusClass(value){
  if(value === 'on_time') return 'ok'
  if(value === 'late') return 'warn'
  return 'muted'
}

export default function Attendance(){
  const [view, setView] = useState('daily') // 'daily' | 'weekly' | 'monthly' | 'records'

  const [dailyDate, setDailyDate] = useState(TODAY_ISO)
  const [dailyReport, setDailyReport] = useState(null)
  const [dailyLoading, setDailyLoading] = useState(false)
  const [dailyError, setDailyError] = useState('')

  const [weeklyReport, setWeeklyReport] = useState(null)
  const [weeklyLoading, setWeeklyLoading] = useState(false)
  const [weeklyError, setWeeklyError] = useState('')

  const [monthlyReport, setMonthlyReport] = useState(null)
  const [monthFilter, setMonthFilter] = useState(CURRENT_MONTH)
  const [yearFilter, setYearFilter] = useState(CURRENT_YEAR)
  const [monthlyLoading, setMonthlyLoading] = useState(false)
  const [monthlyError, setMonthlyError] = useState('')

  const [filters, setFilters] = useState({ employee: '', date_from: '', date_to: '', status: '' })
  const [selectedEmployeeOption, setSelectedEmployeeOption] = useState(null)
  const [records, setRecords] = useState([])
  const [recordsCount, setRecordsCount] = useState(0)
  const [recordsPage, setRecordsPage] = useState(1)
  const [recordsNext, setRecordsNext] = useState(null)
  const [recordsPrevious, setRecordsPrevious] = useState(null)
  const [recordsLoading, setRecordsLoading] = useState(false)
  const [recordsError, setRecordsError] = useState('')

  useEffect(()=>{
    loadDailyReport(TODAY_ISO)
    loadAttendanceRecords(1)
  }, [])

  useEffect(()=>{
    if(dailyError) notifyError(dailyError)
  }, [dailyError])

  useEffect(()=>{
    if(weeklyError) notifyError(weeklyError)
  }, [weeklyError])

  useEffect(()=>{
    if(monthlyError) notifyError(monthlyError)
  }, [monthlyError])

  useEffect(()=>{
    if(recordsError) notifyError(recordsError)
  }, [recordsError])

  async function loadDailyReport(dateValue = dailyDate){
    setDailyLoading(true)
    setDailyError('')
    try{
      const data = await api.getDailyReport({ date: dateValue || TODAY_ISO })
      setDailyReport(data || null)
    }catch(requestError){
      setDailyError(requestError.message || 'Unable to load daily report')
    }finally{
      setDailyLoading(false)
    }
  }

  async function loadWeeklyReport(){
    setWeeklyLoading(true)
    setWeeklyError('')
    try{
      const data = await api.getWeeklyReport()
      setWeeklyReport(data || null)
    }catch(requestError){
      setWeeklyError(requestError.message || 'Unable to load weekly report')
    }finally{
      setWeeklyLoading(false)
    }
  }

  async function loadMonthlyReport(monthValue = monthFilter, yearValue = yearFilter){
    setMonthlyLoading(true)
    setMonthlyError('')
    try{
      const data = await api.getMonthlyReport({ month: monthValue, year: yearValue })
      setMonthlyReport(data || null)
    }catch(requestError){
      setMonthlyError(requestError.message || 'Unable to load monthly report')
    }finally{
      setMonthlyLoading(false)
    }
  }

  async function loadAttendanceRecords(page = recordsPage, sourceFilters = filters){
    setRecordsLoading(true)
    setRecordsError('')
    try{
      const params = { page }
      if(sourceFilters.employee) params.employee = sourceFilters.employee
      if(sourceFilters.date_from) params.date_from = sourceFilters.date_from
      if(sourceFilters.date_to) params.date_to = sourceFilters.date_to
      if(sourceFilters.status) params.status = sourceFilters.status

      const data = await api.getAttendance(params)
      const rows = data.results || data || []
      const normalizedRows = Array.isArray(rows) ? rows : []

      setRecords(normalizedRows)
      setRecordsCount(Number.isFinite(data.count) ? data.count : normalizedRows.length)
      setRecordsNext(data.next || null)
      setRecordsPrevious(data.previous || null)
      setRecordsPage(page)
    }catch(requestError){
      setRecordsError(requestError.message || 'Unable to load attendance records')
    }finally{
      setRecordsLoading(false)
    }
  }

  function switchView(nextView){
    setView(nextView)
    if(nextView === 'daily'){
      loadDailyReport(dailyDate)
      return
    }

    if(nextView === 'weekly'){
      loadWeeklyReport()
      return
    }

    if(nextView === 'monthly'){
      loadMonthlyReport(monthFilter, yearFilter)
      return
    }

    loadAttendanceRecords(recordsPage)
  }

  function applyFilters(event){
    event.preventDefault()
    loadAttendanceRecords(1)
  }

  function resetFilters(){
    const nextFilters = { employee: '', date_from: '', date_to: '', status: '' }
    setFilters(nextFilters)
    setSelectedEmployeeOption(null)
    loadAttendanceRecords(1, nextFilters)
  }

  const dailyRows = dailyReport?.attendance_details || []
  const weeklyRows = weeklyReport?.attendance_details || []
  const monthlyRows = Array.isArray(monthlyReport?.employee_summary)
    ? monthlyReport.employee_summary
    : (Array.isArray(monthlyReport?.attendance_details) ? monthlyReport.attendance_details : [])

  return (
    <div className="page-stack">
      <section className="surface">
        {/* <div className="section-heading">
          <h2>Attendance Center</h2>
          <span>Daily insights and full attendance history</span>
        </div> */}

        <div className="attendance-tabs">
          <button
            className={view === 'daily' ? 'btn primary' : 'btn secondary'}
            type="button"
            onClick={()=> switchView('daily')}
          >
            Daily Reports
          </button>
          <button
            className={view === 'weekly' ? 'btn primary' : 'btn secondary'}
            type="button"
            onClick={()=> switchView('weekly')}
          >
            Weekly Reports
          </button>
          <button
            className={view === 'monthly' ? 'btn primary' : 'btn secondary'}
            type="button"
            onClick={()=> switchView('monthly')}
          >
            Monthly Reports
          </button>
          <button
            className={view === 'records' ? 'btn primary' : 'btn secondary'}
            type="button"
            onClick={()=> switchView('records')}
          >
            Attendance Records
          </button>
        </div>

        {view === 'daily' && (
          <>
            <div className="section-heading">
              <h3>Daily Report</h3>
              <div className="inline-form compact">
                <DatePickerField value={dailyDate} onChange={setDailyDate} />
                <button className="btn secondary" type="button" onClick={()=> loadDailyReport(dailyDate)} disabled={dailyLoading}>
                  {dailyLoading ? 'Loading...' : 'Load'}
                </button>
                <button
                  className="btn secondary"
                  type="button"
                  onClick={()=>{
                    setDailyDate(TODAY_ISO)
                    loadDailyReport(TODAY_ISO)
                  }}
                >
                  Today
                </button>
              </div>
            </div>
            <div className="daily-metrics">
              <div className="metric-tile">
                <p className="metric-title">Active Employees</p>
                <div className="metric-main">{dailyReport?.total_active_employees || 0}</div>
              </div>

              <div className="metric-tile">
                <p className="metric-title">Present</p>
                <div className="metric-main">{dailyReport?.present || 0}</div>
              </div>

              <div className="metric-tile">
                <p className="metric-title">Absent</p>
                <div className="metric-main">{dailyReport?.absent || 0}</div>
              </div>

              <div className="metric-tile">
                <p className="metric-title">On Time</p>
                <div className="metric-main">{dailyReport?.on_time || 0}</div>
              </div>

              <div className="metric-tile">
                <p className="metric-title">Late</p>
                <div className="metric-main">{dailyReport?.late || 0}</div>
              </div>
            </div>

            <div className="attendance-meta">
              <p className="attendance-meta-text">Showing records for {formatDate(dailyDate)}</p>
              <p className="attendance-meta-text">{dailyRows.length} records</p>
            </div>

            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Employee</th>
                    <th>Check In</th>
                    <th>Check Out</th>
                    <th>Total Hours</th>
                    <th>Status</th>
                    <th>Late Message</th>
                  </tr>
                </thead>
                <tbody>
                  {dailyLoading && (
                    <tr>
                      <td colSpan="6" className="empty-row">Loading daily records...</td>
                    </tr>
                  )}

                  {!dailyLoading && dailyRows.length === 0 && (
                    <tr>
                      <td colSpan="6" className="empty-row">No records found for this date.</td>
                    </tr>
                  )}

                  {!dailyLoading && dailyRows.map((row)=> (
                    <tr key={row.id}>
                      <td>{row.employee_name || row.employee || '-'}</td>
                      <td>{formatTime12(row.check_in)}</td>
                      <td>{formatTime12(row.check_out)}</td>
                      <td>{row.total_hours ?? '-'}</td>
                      <td>
                        <span className={`status-badge ${statusClass(row.status)}`}>
                          {statusLabel(row.status)}
                        </span>
                      </td>
                      <td className="truncate-cell">{row.message_late || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {view === 'weekly' && (
          <>
            <div className="section-heading">
              <h3>Weekly Report</h3>
              <button className="btn secondary" type="button" onClick={loadWeeklyReport} disabled={weeklyLoading}>
                {weeklyLoading ? 'Loading...' : 'Refresh'}
              </button>
            </div>
            <div className="daily-metrics">
              <div className="metric-tile">
                <p className="metric-title">Total Records</p>
                <div className="metric-main">{weeklyReport?.total_records ?? 0}</div>
              </div>

              <div className="metric-tile">
                <p className="metric-title">Total Hours</p>
                <div className="metric-main">{weeklyReport?.total_hours ?? 0}</div>
              </div>

              <div className="metric-tile">
                <p className="metric-title">Late Arrivals</p>
                <div className="metric-main">{weeklyReport?.late_arrivals ?? 0}</div>
              </div>

              <div className="metric-tile">
                <p className="metric-title">Avg Hours / Day</p>
                <div className="metric-main">{weeklyReport?.average_hours_per_day ?? 0}</div>
              </div>
            </div>

            {Array.isArray(weeklyRows) && weeklyRows.length > 0 && (
              <div className="table-scroll" style={{ marginTop: 12 }}>
                <table>
                  <thead>
                    <tr>
                      <th>Employee</th>
                      <th>Date</th>
                      <th>Check In</th>
                      <th>Check Out</th>
                      <th>Total Hours</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {weeklyRows.map((row)=> (
                      <tr key={row.id}>
                        <td>{row.employee_name || row.employee || '-'}</td>
                        <td>{formatDate(row.date)}</td>
                        <td>{formatTime12(row.check_in)}</td>
                        <td>{formatTime12(row.check_out)}</td>
                        <td>{row.total_hours ?? '-'}</td>
                        <td>
                          <span className={`status-badge ${statusClass(row.status)}`}>
                            {statusLabel(row.status)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {view === 'monthly' && (
          <>
            <div className="section-heading">
              <h3>Monthly Report</h3>
              <div className="inline-form compact">
                <select value={monthFilter} onChange={(event)=> setMonthFilter(event.target.value)}>
                  {MONTH_OPTIONS.map((month)=> (
                    <option key={month.value} value={month.value}>{month.label}</option>
                  ))}
                </select>
                <input
                  type="number"
                  min="2000"
                  max="2100"
                  value={yearFilter}
                  onChange={(event)=> setYearFilter(event.target.value)}
                />
                <button
                  className="btn secondary"
                  type="button"
                  onClick={()=> loadMonthlyReport(monthFilter, yearFilter)}
                  disabled={monthlyLoading}
                >
                  {monthlyLoading ? 'Loading...' : 'Load'}
                </button>
                <button
                  className="btn secondary"
                  type="button"
                  onClick={()=>{
                    setMonthFilter(CURRENT_MONTH)
                    setYearFilter(CURRENT_YEAR)
                    loadMonthlyReport(CURRENT_MONTH, CURRENT_YEAR)
                  }}
                >
                  Current Month
                </button>
              </div>
            </div>
            <div className="daily-metrics">
              <div className="metric-tile">
                <p className="metric-title">Working Days</p>
                <div className="metric-main">{monthlyReport?.total_working_days ?? 0}</div>
              </div>

              <div className="metric-tile">
                <p className="metric-title">Hours Worked</p>
                <div className="metric-main">{monthlyReport?.total_hours_worked ?? 0}</div>
              </div>

              <div className="metric-tile">
                <p className="metric-title">Unique Employees</p>
                <div className="metric-main">{monthlyReport?.unique_employees ?? 0}</div>
              </div>

              <div className="metric-tile">
                <p className="metric-title">Late Arrivals</p>
                <div className="metric-main">{monthlyReport?.late_arrivals ?? 0}</div>
              </div>
            </div>

            {Array.isArray(monthlyRows) && monthlyRows.length > 0 && (
              <div className="table-scroll" style={{ marginTop: 12 }}>
                <table>
                  <thead>
                    <tr>
                      <th>Employee</th>
                      <th>Present Days</th>
                      <th>Total Hours</th>
                      <th>Late Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {monthlyRows.map((row, index)=> (
                      <tr key={row.id || `${row.employee || row.employee_name || 'row'}-${index}`}>
                        <td>{row.employee_name || row.employee || '-'}</td>
                        <td>{row.present_days ?? row.total_days_worked ?? '-'}</td>
                        <td>{row.total_hours ?? row.total_hours_worked ?? '-'}</td>
                        <td>{row.late_count ?? row.late_arrivals ?? row.late ?? '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {view === 'records' && (
          <>
            <div className="section-heading">
              <h3>Attendance Records</h3>
              <span>{recordsCount} total records</span>
            </div>

            <form className="form-grid attendance-filters" onSubmit={applyFilters}>
              <label>
                Employee
                <AsyncSelect
                  cacheOptions
                  defaultOptions
                  className="leave-employee-select"
                  classNamePrefix="rs"
                  value={selectedEmployeeOption}
                  loadOptions={async (inputValue) => {
                    try{
                      const data = await api.getEmployees({ search: inputValue, page_size: 20 })
                      const rows = data.results || data || []
                      return (Array.isArray(rows) ? rows : []).map((employee) => ({
                        label: `${employee.name || employee.employee_name || employee.emp_id}` + (employee.emp_id ? ` • ${employee.emp_id}` : ''),
                        value: employee.emp_id || employee.id
                      }))
                    }catch(error){
                      return []
                    }
                  }}
                  onChange={(option)=>{
                    setSelectedEmployeeOption(option)
                    setFilters((prev)=> ({ ...prev, employee: option ? option.value : '' }))
                  }}
                  placeholder="Select employee..."
                />
              </label>

              <label>
                From Date
                <DatePickerField
                  value={filters.date_from}
                  onChange={(value)=> setFilters((prev)=> ({ ...prev, date_from: value }))}
                />
              </label>

              <label>
                To Date
                <DatePickerField
                  value={filters.date_to}
                  onChange={(value)=> setFilters((prev)=> ({ ...prev, date_to: value }))}
                />
              </label>

              <label>
                Status
                <select
                  value={filters.status}
                  onChange={(event)=> setFilters((prev)=> ({ ...prev, status: event.target.value }))}
                >
                  <option value="">All</option>
                  <option value="on_time">On Time</option>
                  <option value="late">Late</option>
                  <option value="absent">Absent</option>
                </select>
              </label>

              <div className="form-actions">
                <button className="btn secondary" type="button" onClick={resetFilters} disabled={recordsLoading}>Reset</button>
                <button className="btn primary" type="submit" disabled={recordsLoading}>
                  {recordsLoading ? 'Loading...' : 'Apply Filters'}
                </button>
              </div>
            </form>
            <div className="attendance-meta">
              <p className="attendance-meta-text">Page {recordsPage}</p>
              <div className="row-actions">
                <button
                  className="btn secondary"
                  type="button"
                  onClick={()=> loadAttendanceRecords(recordsPage - 1)}
                  disabled={!recordsPrevious || recordsLoading || recordsPage <= 1}
                >
                  Previous
                </button>
                <button
                  className="btn secondary"
                  type="button"
                  onClick={()=> loadAttendanceRecords(recordsPage + 1)}
                  disabled={!recordsNext || recordsLoading}
                >
                  Next
                </button>
              </div>
            </div>

            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Employee</th>
                    <th>Date</th>
                    <th>Check In</th>
                    <th>Check Out</th>
                    <th>Total Hours</th>
                    <th>Status</th>
                    <th>Late Message</th>
                  </tr>
                </thead>
                <tbody>
                  {recordsLoading && (
                    <tr>
                      <td colSpan="7" className="empty-row">Loading attendance records...</td>
                    </tr>
                  )}

                  {!recordsLoading && records.length === 0 && (
                    <tr>
                      <td colSpan="7" className="empty-row">No attendance records found for current filters.</td>
                    </tr>
                  )}

                  {!recordsLoading && records.map((record)=> (
                    <tr key={record.id}>
                      <td>{record.employee_name || record.employee || '-'}</td>
                      <td>{formatDate(record.date)}</td>
                      <td>{formatDateTime(record.check_in)}</td>
                      <td>{formatDateTime(record.check_out)}</td>
                      <td>{record.total_hours ?? '-'}</td>
                      <td>
                        <span className={`status-badge ${statusClass(record.status)}`}>
                          {statusLabel(record.status)}
                        </span>
                      </td>
                      <td className="truncate-cell">{record.message_late || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
    </div>
  )
}
