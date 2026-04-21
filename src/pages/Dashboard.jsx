import React, { useEffect, useMemo, useState } from 'react'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import { notifyError, notifySuccess } from '../services/notify'

const defaultStats = {
  total_employees: 0,
  active_employees: 0,
  inactive_employees: 0,
  present_today: 0
}

export default function Dashboard(){
  const [stats, setStats] = useState(defaultStats)
  const [dailyReport, setDailyReport] = useState(null)
  const [weeklyReport, setWeeklyReport] = useState(null)
  const [monthlyReport, setMonthlyReport] = useState(null)
  const [pendingLeaves, setPendingLeaves] = useState([])
  const [loading, setLoading] = useState(true)
  const { displayName, auth } = useAuth()
  const [actionProcessingId, setActionProcessingId] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)

  const now = useMemo(()=> new Date(), [])
  const dailyDate = useMemo(()=> now.toISOString().split('T')[0], [now])

  useEffect(()=>{
    loadDashboard()
  }, [])

  async function loadDashboard(){
    setLoading(true)
    const month = now.getMonth() + 1
    const year = now.getFullYear()

    const [statsResult, dailyResult, weeklyResult, monthlyResult, pendingResult] = await Promise.allSettled([
      api.getEmployeeStats(),
      api.getDailyReport({ date: dailyDate }),
      api.getWeeklyReport(),
      api.getMonthlyReport({ month, year }),
      (auth && auth.role === 'manager') ? Promise.resolve({ leaves: [] }) : api.getPendingApprovals()
    ])

    if(statsResult.status === 'fulfilled'){
      setStats({
        total_employees: statsResult.value.total_employees || 0,
        active_employees: statsResult.value.active_employees || 0,
        inactive_employees: statsResult.value.inactive_employees || 0,
        present_today: statsResult.value.present_today || 0
      })
    }

    if(dailyResult.status === 'fulfilled'){
      setDailyReport(dailyResult.value)
    }

    if(weeklyResult.status === 'fulfilled'){
      setWeeklyReport(weeklyResult.value)
    }

    if(monthlyResult.status === 'fulfilled'){
      setMonthlyReport(monthlyResult.value)
    }

    if(pendingResult && pendingResult.status === 'fulfilled'){
      setPendingLeaves(pendingResult.value.leaves || pendingResult.value.results || [])
    }

    const hasFailure = [statsResult, dailyResult, weeklyResult, monthlyResult, pendingResult].some((result)=> result.status === 'rejected')
    if(hasFailure){
      notifyError('Some dashboard data could not be loaded. Check API availability and try refreshing.')
    }

    setLoading(false)
    setLastUpdated(new Date())
  }

  async function handleApprove(leaveId){
    const ok = window.confirm('Approve this leave request?')
    if(!ok) return
    setActionProcessingId(leaveId)
    try{
      await api.approveLeave(leaveId, { approved_by: displayName || '' })
      setPendingLeaves((prev)=> prev.filter((l)=> l.id !== leaveId))
      notifySuccess('Leave approved successfully')
    }catch(err){
      const msg = err?.message || 'Unable to approve leave'
      notifyError(msg)
    }finally{
      setActionProcessingId(null)
    }
  }

  async function handleReject(leaveId){
    const ok = window.confirm('Reject this leave request?')
    if(!ok) return
    setActionProcessingId(leaveId)
    try{
      await api.rejectLeave(leaveId, { approved_by: displayName || '' })
      setPendingLeaves((prev)=> prev.filter((l)=> l.id !== leaveId))
      notifySuccess('Leave rejected successfully')
    }catch(err){
      const msg = err?.message || 'Unable to reject leave'
      notifyError(msg)
    }finally{
      setActionProcessingId(null)
    }
  }

  return (
    <div className="space-y-4" style={{ animation: 'rise 0.45s ease both' }}>
        <section className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">Operations Snapshot</h2>
            {/* <p className="text-sm text-gray-600">Live attendance, approvals, and workforce metrics from the EMS backend.</p> */}
          </div>
          <div className="flex items-center gap-3">
            <button className="px-3 py-2 bg-gray-100 rounded-md" onClick={loadDashboard} disabled={loading}>
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
            <span className="text-sm text-gray-500">{lastUpdated ? `Last refresh: ${lastUpdated.toLocaleString()}` : ''}</span>
          </div>
        </section>
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <article className="rounded-xl p-4 text-white bg-gradient-to-br from-amber-500 to-orange-500 shadow-md">
          <p className="text-sm">Total Employees</p>
          <h3 className="text-2xl font-semibold">{loading ? <span className="inline-block w-16 h-6 bg-white/30 rounded animate-pulse" /> : stats.total_employees}</h3>
          <span className="text-xs opacity-90">Registered records</span>
        </article>
        <article className="rounded-xl p-4 text-white bg-gradient-to-br from-teal-600 to-emerald-600 shadow-md">
          <p className="text-sm">Active Employees</p>
          <h3 className="text-2xl font-semibold">{loading ? <span className="inline-block w-16 h-6 bg-white/30 rounded animate-pulse" /> : stats.active_employees}</h3>
          <span className="text-xs opacity-90">Currently active status</span>
        </article>
        <article className="rounded-xl p-4 text-white bg-gradient-to-br from-slate-700 to-slate-800 shadow-md">
          <p className="text-sm">Present Today</p>
          <h3 className="text-2xl font-semibold">{loading ? <span className="inline-block w-16 h-6 bg-white/30 rounded animate-pulse" /> : stats.present_today}</h3>
          <span className="text-xs opacity-90">Based on daily report</span>
        </article>
        <article className="rounded-xl p-4 text-white bg-gradient-to-br from-rose-500 to-red-600 shadow-md">
          <p className="text-sm">Pending Leaves</p>
          <h3 className="text-2xl font-semibold">{loading ? <span className="inline-block w-16 h-6 bg-white/30 rounded animate-pulse" /> : pendingLeaves.length}</h3>
          <span className="text-xs opacity-90">Approval workflow queue</span>
        </article>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
          <h3 className="text-lg font-semibold mb-3">Daily Attendance</h3>
          <ul className="grid gap-2">
            <li className="flex justify-between items-center bg-gray-50 border border-gray-100 rounded-md p-3"><span className="text-sm text-gray-700">Present</span><strong className="text-gray-900">{dailyReport?.present || 0}</strong></li>
            <li className="flex justify-between items-center bg-gray-50 border border-gray-100 rounded-md p-3"><span className="text-sm text-gray-700">Absent</span><strong className="text-gray-900">{dailyReport?.absent || 0}</strong></li>
            <li className="flex justify-between items-center bg-gray-50 border border-gray-100 rounded-md p-3"><span className="text-sm text-gray-700">On Time</span><strong className="text-gray-900">{dailyReport?.on_time || 0}</strong></li>
            <li className="flex justify-between items-center bg-gray-50 border border-gray-100 rounded-md p-3"><span className="text-sm text-gray-700">Late</span><strong className="text-gray-900">{dailyReport?.late || 0}</strong></li>
          </ul>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
          <h3 className="text-lg font-semibold mb-3">Weekly Summary</h3>
          <ul className="grid gap-2">
            <li className="flex justify-between items-center bg-gray-50 border border-gray-100 rounded-md p-3"><span className="text-sm text-gray-700">Total Records</span><strong className="text-gray-900">{weeklyReport?.total_records || 0}</strong></li>
            <li className="flex justify-between items-center bg-gray-50 border border-gray-100 rounded-md p-3"><span className="text-sm text-gray-700">Total Hours</span><strong className="text-gray-900">{weeklyReport?.total_hours || 0}</strong></li>
            <li className="flex justify-between items-center bg-gray-50 border border-gray-100 rounded-md p-3"><span className="text-sm text-gray-700">Late Arrivals</span><strong className="text-gray-900">{weeklyReport?.late_arrivals || 0}</strong></li>
            <li className="flex justify-between items-center bg-gray-50 border border-gray-100 rounded-md p-3"><span className="text-sm text-gray-700">Avg / Day</span><strong className="text-gray-900">{weeklyReport?.average_hours_per_day || 0}</strong></li>
          </ul>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
          <h3 className="text-lg font-semibold mb-3">Monthly Analysis</h3>
          <ul className="grid gap-2">
            <li className="flex justify-between items-center bg-gray-50 border border-gray-100 rounded-md p-3"><span className="text-sm text-gray-700">Employees</span><strong className="text-gray-900">{monthlyReport?.unique_employees || 0}</strong></li>
            <li className="flex justify-between items-center bg-gray-50 border border-gray-100 rounded-md p-3"><span className="text-sm text-gray-700">Total Hours</span><strong className="text-gray-900">{monthlyReport?.total_hours_worked || 0}</strong></li>
            <li className="flex justify-between items-center bg-gray-50 border border-gray-100 rounded-md p-3"><span className="text-sm text-gray-700">Working Days</span><strong className="text-gray-900">{monthlyReport?.total_working_days || 0}</strong></li>
            <li className="flex justify-between items-center bg-gray-50 border border-gray-100 rounded-md p-3"><span className="text-sm text-gray-700">Late Arrivals</span><strong className="text-gray-900">{monthlyReport?.late_arrivals || 0}</strong></li>
          </ul>
        </div>
      </section>

      {auth?.role !== 'manager' && (
      <section className="bg-white border border-gray-200 rounded-xl p-4">
        <div className="flex items-center justify-between gap-2 mb-3">
          <h3 className="text-lg font-semibold">Pending Leave Approvals</h3>
          <span className="text-sm text-gray-600">{pendingLeaves.length} awaiting decision</span>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full table-auto" aria-label="Pending leave approvals">
            <thead>
              <tr>
                <th className="text-left text-xs font-semibold text-gray-600 uppercase tracking-wider px-4 py-2">Employee ID</th>
                <th className="text-left text-xs font-semibold text-gray-600 uppercase tracking-wider px-4 py-2">Name</th>
                <th className="text-left text-xs font-semibold text-gray-600 uppercase tracking-wider px-4 py-2">Reason</th>
                <th className="text-left text-xs font-semibold text-gray-600 uppercase tracking-wider px-4 py-2">Start Date</th>
                <th className="text-left text-xs font-semibold text-gray-600 uppercase tracking-wider px-4 py-2">End Date</th>
                <th className="text-left text-xs font-semibold text-gray-600 uppercase tracking-wider px-4 py-2">Duration</th>
                <th className="text-left text-xs font-semibold text-gray-600 uppercase tracking-wider px-4 py-2">Status</th>
                <th className="text-left text-xs font-semibold text-gray-600 uppercase tracking-wider px-4 py-2">Approved By</th>
                <th className="text-left text-xs font-semibold text-gray-600 uppercase tracking-wider px-4 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {pendingLeaves.length === 0 && (
                <tr>
                  <td colSpan="9" className="text-center text-gray-500 p-4">No pending requests right now.</td>
                </tr>
              )}

              {pendingLeaves.map((leave)=> (
                <tr key={leave.id} className="hover:bg-gray-50 odd:bg-white even:bg-gray-50">
                  <td className="px-4 py-3">{leave.employee ?? '-'}</td>
                  <td className="px-4 py-3">{leave.employee_name ?? '-'}</td>
                  <td className="max-w-xs truncate px-4 py-3">{`${leave.leave_type || ''}${leave.reason ? ': ' + leave.reason : ''}` || '-'}</td>
                  <td className="px-4 py-3">{leave.start_time ? String(leave.start_time).split('T')[0] : '-'}</td>
                  <td className="px-4 py-3">{leave.end_time ? String(leave.end_time).split('T')[0] : '-'}</td>
                  <td className="px-4 py-3">{leave.duration_days ?? leave.duration ?? '-'}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center justify-center rounded-full text-xs font-semibold px-2 py-1 ${leave.approved ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'}`}>
                      {leave.approved ? 'Approved' : 'Not Approved'}
                    </span>
                  </td>
                  <td className="px-4 py-3">{leave.approved_by || '-'}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <button
                        className="px-3 py-2 bg-emerald-600 text-white rounded-lg font-semibold disabled:opacity-60 disabled:cursor-not-allowed"
                        disabled={actionProcessingId === leave.id}
                        onClick={()=> handleApprove(leave.id)}
                      >
                        {actionProcessingId === leave.id ? 'Processing...' : 'Approve'}
                      </button>

                      <button
                        className="px-3 py-2 bg-red-600 text-white rounded-lg font-semibold disabled:opacity-60 disabled:cursor-not-allowed"
                        disabled={actionProcessingId === leave.id}
                        onClick={()=> handleReject(leave.id)}
                      >
                        {actionProcessingId === leave.id ? 'Processing...' : 'Reject'}
                      </button>
                    </div>
                  </td>
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
