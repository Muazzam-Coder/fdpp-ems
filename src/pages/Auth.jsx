import React, { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'
import { notifyError, notifySuccess, notifyWarning } from '../services/notify'

const loginDefaults = {
  username: '',
  password: ''
}

const attendanceDefaults = {
  empId: ''
}

export default function AuthPage(){
  const navigate = useNavigate()
  const location = useLocation()
  const { login, sessionNotice } = useAuth()

  const [busy, setBusy] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [loginForm, setLoginForm] = useState(loginDefaults)
  const [attendanceForm, setAttendanceForm] = useState(attendanceDefaults)
  const [attendanceBusy, setAttendanceBusy] = useState(false)
  const [attendanceError, setAttendanceError] = useState('')
  const [attendanceMessage, setAttendanceMessage] = useState('')

  const redirectTarget = useMemo(()=>{
    const from = location.state?.from
    if(from && typeof from === 'object' && typeof from.pathname === 'string'){
      return from.pathname
    }
    return '/'
  }, [location.state])

  useEffect(()=>{
    if(!sessionNotice) return
    notifyWarning(sessionNotice, { id: 'auth-session-notice' })
  }, [sessionNotice])

  async function submitLogin(event){
    event.preventDefault()
    setBusy(true)

    try{
      await login({
        username: loginForm.username.trim(),
        password: loginForm.password
      })
      notifySuccess('Signed in successfully')
      navigate(redirectTarget, { replace: true })
    }catch(requestError){
      notifyError(requestError.message || 'Unable to sign in with those credentials')
    }finally{
      setBusy(false)
    }
  }

  async function submitAttendance(actionType){
    const empId = attendanceForm.empId.trim()
    if(!empId){
      setAttendanceError('Employee ID is required')
      setAttendanceMessage('')
      return
    }

    setAttendanceBusy(true)
    setAttendanceError('')
    setAttendanceMessage('')

    try{
      const data = actionType === 'in'
        ? await api.checkIn(empId)
        : await api.checkOut(empId)

      setAttendanceMessage(data?.message || (actionType === 'in' ? 'Check-in successful' : 'Check-out successful'))
    }catch(requestError){
      setAttendanceError(requestError.message || 'Unable to complete attendance request')
    }finally{
      setAttendanceBusy(false)
    }
  }

  const inputBase = 'w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100'
  const labelBase = 'flex flex-col gap-1 text-sm font-medium text-slate-600'
  const primaryBtn = 'inline-flex items-center justify-center rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-60'
  const secondaryBtn = 'inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100'

  return (
    <div className="grid min-h-screen place-items-center p-5 max-[720px]:p-3">
      <section className="grid w-full max-w-[1080px] overflow-hidden rounded-[22px] border border-slate-200 bg-white shadow-[0_20px_40px_rgba(22,41,56,0.08)] md:grid-cols-[minmax(280px,0.86fr)_minmax(360px,1.14fr)]">
        <aside className="grid content-between gap-4 bg-[linear-gradient(160deg,#0b5e65_0%,#0b3b52_55%,#0f293f_100%)] p-7 text-[#eaf7fb] max-[980px]:gap-3">
          <div>
            <img src="/logo.png" alt="FDPP" className="mb-4 block w-full max-w-[220px] rounded-[10px] bg-white p-1" />
            <h1 className="m-0 font-[Space_Grotesk,Sora,sans-serif] text-2xl leading-tight">FDPP Employee Management</h1>
          </div>
        </aside>

        <div className="grid content-start gap-3 p-6 max-[720px]:p-4">
          <div>
            <h2 className="m-0 font-[Space_Grotesk,Sora,sans-serif] text-[1.4rem]">Sign In</h2>
          </div>

          <form className="grid gap-3" onSubmit={submitLogin}>
            <label className={labelBase}>
              Username
              <input
                className={inputBase}
                value={loginForm.username}
                required
                autoComplete="username"
                onChange={(event)=> setLoginForm({ ...loginForm, username: event.target.value })}
              />
            </label>

            <label className={labelBase}>
              Password
              <div className="grid grid-cols-[1fr_auto] items-stretch gap-2">
                <input
                  className={inputBase}
                  type={showPassword ? 'text' : 'password'}
                  value={loginForm.password}
                  required
                  autoComplete="current-password"
                  onChange={(event)=> setLoginForm({ ...loginForm, password: event.target.value })}
                />
                <button
                  className={secondaryBtn}
                  type="button"
                  onClick={()=> setShowPassword((value)=> !value)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  <i className={`fa ${showPassword ? 'fa-eye-slash' : 'fa-eye'}`}></i>
                </button>
              </div>
            </label>

            <div className="mt-1 flex flex-wrap items-center justify-between gap-2">
              <button className={primaryBtn} type="submit" disabled={busy}>
                {busy ? 'Signing in...' : 'Sign In'}
              </button>
            </div>
          </form>
          
        </div>
      </section>
    </div>
  )
}
