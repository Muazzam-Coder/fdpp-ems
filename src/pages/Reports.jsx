import React, { useState } from 'react'
import AsyncSelect from 'react-select/async'
import api from '../services/api'
import { formatDateRangeText } from '../utils/dateTime'
import DatePickerField from '../components/DatePickerField'
import { notifyError, notifySuccess } from '../services/notify'

export default function Reports(){
  const [payoutForm, setPayoutForm] = useState({ emp_id: '', start_date: '', end_date: '' })
  const [attendanceForm, setAttendanceForm] = useState({ emp_id: '', period: 'month', start_date: '', end_date: '' })
  const [selectedPayoutOption, setSelectedPayoutOption] = useState(null)
  const [selectedAttendanceOption, setSelectedAttendanceOption] = useState(null)

  const [payoutResult, setPayoutResult] = useState(null)
  const [attendanceResult, setAttendanceResult] = useState(null)

  async function loadPayout(event){
    event.preventDefault()
    try{
      const data = await api.calculatePayout(payoutForm.emp_id, {
        start_date: payoutForm.start_date,
        end_date: payoutForm.end_date
      })
      setPayoutResult(data)
      notifySuccess('Payout report loaded successfully')
    }catch(requestError){
      notifyError(requestError.message || 'Unable to load payout report')
    }
  }

  async function loadAttendanceReport(event){
    event.preventDefault()
    try{
      const params = { period: attendanceForm.period }
      if(attendanceForm.start_date) params.start_date = attendanceForm.start_date
      if(attendanceForm.end_date) params.end_date = attendanceForm.end_date
      const data = await api.getEmployeeAttendanceReport(attendanceForm.emp_id, params)
      setAttendanceResult(data)
      notifySuccess('Attendance report loaded successfully')
    }catch(requestError){
      notifyError(requestError.message || 'Unable to load attendance report')
    }
  }

  return (
    <div className="page-stack">
      <section className="surface split-grid">
        <article>
          <h2>Payroll Report</h2>
          <form className="form-grid" onSubmit={loadPayout}>
            <label>
              Employee ID
              <AsyncSelect
                cacheOptions
                defaultOptions
                className="leave-employee-select"
                classNamePrefix="rs"
                value={selectedPayoutOption}
                loadOptions={async (inputValue) => {
                  try{
                    const data = await api.getEmployees({ search: inputValue, page_size: 20 })
                    const rows = data.results || data || []
                    return (Array.isArray(rows) ? rows : []).map(r => ({ label: `${r.name || r.employee_name || r.emp_id}` + (r.emp_id ? ` • ${r.emp_id}` : ''), value: r.emp_id || r.id, raw: r }))
                  }catch(e){
                    return []
                  }
                }}
                onChange={(option)=>{
                  setSelectedPayoutOption(option)
                  setPayoutForm({ ...payoutForm, emp_id: option ? option.value : '' })
                }}
                placeholder="Select employee..."
                required
              />
            </label>
            <label>
              Start Date
              <DatePickerField
                value={payoutForm.start_date}
                onChange={(value)=> setPayoutForm({ ...payoutForm, start_date: value })}
                required
              />
            </label>
            <label>
              End Date
              <DatePickerField
                value={payoutForm.end_date}
                onChange={(value)=> setPayoutForm({ ...payoutForm, end_date: value })}
                required
              />
            </label>
            <div className="form-actions">
              <button className="btn primary" type="submit">Calculate Payout</button>
            </div>
          </form>

          {payoutResult && (
            <div className="report-grid">
              <article>
                <p>Employee</p>
                <h4>{payoutResult.employee_name}</h4>
                <small>{payoutResult.employee_id}</small>
              </article>
              <article>
                <p>Total Hours</p>
                <h4>{payoutResult.total_hours}</h4>
                <small>Overtime: {payoutResult.overtime_hours}</small>
              </article>
              <article>
                <p>Base + Overtime</p>
                <h4>{payoutResult.base_payout} + {payoutResult.overtime_payout}</h4>
                <small>Hourly: {payoutResult.hourly_rate}</small>
              </article>
              <article>
                <p>Total Payout</p>
                <h4>{payoutResult.total_payout}</h4>
                <small>{formatDateRangeText(payoutResult.period)}</small>
              </article>
            </div>
          )}
        </article>

        <article>
          <h2>Attendance Analytics</h2>
          <form className="form-grid" onSubmit={loadAttendanceReport}>
            <label>
              Employee ID
              <AsyncSelect
                cacheOptions
                defaultOptions
                className="leave-employee-select"
                classNamePrefix="rs"
                value={selectedAttendanceOption}
                loadOptions={async (inputValue) => {
                  try{
                    const data = await api.getEmployees({ search: inputValue, page_size: 20 })
                    const rows = data.results || data || []
                    return (Array.isArray(rows) ? rows : []).map(r => ({ label: `${r.name || r.employee_name || r.emp_id}` + (r.emp_id ? ` • ${r.emp_id}` : ''), value: r.emp_id || r.id, raw: r }))
                  }catch(e){
                    return []
                  }
                }}
                onChange={(option)=>{
                  setSelectedAttendanceOption(option)
                  setAttendanceForm({ ...attendanceForm, emp_id: option ? option.value : '' })
                }}
                placeholder="Select employee..."
                required
              />
            </label>
            <label>
              Period
              <select
                value={attendanceForm.period}
                onChange={(event)=> setAttendanceForm({ ...attendanceForm, period: event.target.value })}
              >
                <option value="day">day</option>
                <option value="week">week</option>
                <option value="month">month</option>
              </select>
            </label>
            <label>
              Start Date
              <DatePickerField
                value={attendanceForm.start_date}
                onChange={(value)=> setAttendanceForm({ ...attendanceForm, start_date: value })}
              />
            </label>
            <label>
              End Date
              <DatePickerField
                value={attendanceForm.end_date}
                onChange={(value)=> setAttendanceForm({ ...attendanceForm, end_date: value })}
              />
            </label>
            <div className="form-actions">
              <button className="btn secondary" type="submit">Load Attendance Report</button>
            </div>
          </form>

          {attendanceResult && (
            <div className="report-grid">
              <article>
                <p>Employee</p>
                <h4>{attendanceResult.employee_name}</h4>
                <small>{attendanceResult.employee_id}</small>
              </article>
              <article>
                <p>Total Days Worked</p>
                <h4>{attendanceResult.total_days_worked || 0}</h4>
                <small>{formatDateRangeText(attendanceResult.period)}</small>
              </article>
              <article>
                <p>Total Hours</p>
                <h4>{attendanceResult.total_hours || 0}</h4>
                <small>On Time: {attendanceResult.on_time || 0}</small>
              </article>
              <article>
                <p>Late Arrivals</p>
                <h4>{attendanceResult.late || 0}</h4>
                <small>Records: {(attendanceResult.attendance_records || []).length}</small>
              </article>
            </div>
          )}
        </article>
      </section>
    </div>
  )
}
