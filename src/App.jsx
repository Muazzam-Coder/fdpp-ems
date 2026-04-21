import React, { useEffect, lazy, Suspense } from 'react'
import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { Toaster } from 'sonner'
import Layout from './components/Layout'
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Employees = lazy(() => import('./pages/Employees'))
const Attendance = lazy(() => import('./pages/Attendance'))
const LeaveManagement = lazy(() => import('./pages/LeaveManagement'))
const Shifts = lazy(() => import('./pages/Shifts'))
const Reports = lazy(() => import('./pages/Reports'))
const Users = lazy(() => import('./pages/Users'))
const AuthPage = lazy(() => import('./pages/Auth'))
const BiometricAttendance = lazy(() => import('./pages/BiometricAttendance'))
import { useAuth } from './context/AuthContext'
import { notifyWarning } from './services/notify'

function AppLoader(){
  return (
    <div className="grid min-h-screen place-items-center p-5">
      <div className="grid justify-items-center gap-2.5 rounded-2xl border border-slate-200 bg-white px-6 py-5 shadow-[0_20px_40px_rgba(22,41,56,0.08)]">
        <span className="h-[22px] w-[22px] animate-spin rounded-full border-2 border-teal-600/20 border-t-teal-600" aria-hidden="true"></span>
        <p className="m-0 text-sm text-slate-500">Preparing your workspace...</p>
      </div>
    </div>
  )
}

function ProtectedLayout(){
  const location = useLocation()
  const { ready, isAuthenticated, sessionNotice, clearSessionNotice } = useAuth()

  useEffect(()=>{
    if(!sessionNotice) return
    notifyWarning(sessionNotice, { id: 'session-notice' })
    clearSessionNotice()
  }, [sessionNotice, clearSessionNotice])

  if(!ready){
    return <AppLoader />
  }

  if(!isAuthenticated){
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return (
    <Layout>
      <Outlet />
    </Layout>
  )
}

function PublicOnlyRoute(){
  const { ready, isAuthenticated } = useAuth()

  if(!ready){
    return <AppLoader />
  }

  if(isAuthenticated){
    return <Navigate to="/" replace />
  }

  return <Outlet />
}

function AuthAwareFallback(){
  const { ready, isAuthenticated } = useAuth()

  if(!ready){
    return <AppLoader />
  }

  return <Navigate to={isAuthenticated ? '/' : '/login'} replace />
}

export default function App(){
  return (
    <>
      <Toaster
        position="top-right"
        richColors
        closeButton
        toastOptions={{
          classNames: {
            toast: 'rounded-xl border border-slate-200 bg-white shadow-lg',
            title: 'text-sm font-semibold text-slate-800',
            description: 'text-xs text-slate-500',
            success: 'border-emerald-200 bg-emerald-50',
            error: 'border-rose-200 bg-rose-50',
            warning: 'border-amber-200 bg-amber-50',
            info: 'border-sky-200 bg-sky-50'
          }
        }}
      />

      <Routes>
        <Route path="/biometric" element={<Suspense fallback={<AppLoader/>}><BiometricAttendance /></Suspense>} />

        <Route element={<PublicOnlyRoute />}>
          <Route path="/login" element={<Suspense fallback={<AppLoader/>}><AuthPage /></Suspense>} />
        </Route>

        <Route element={<ProtectedLayout />}>
          <Route path="/" element={<Suspense fallback={<AppLoader/>}><Dashboard/></Suspense>} />
          <Route path="/employees" element={<Suspense fallback={<AppLoader/>}><Employees/></Suspense>} />
          <Route path="/users" element={<Suspense fallback={<AppLoader/>}><Users/></Suspense>} />
          <Route path="/attendance" element={<Suspense fallback={<AppLoader/>}><Attendance/></Suspense>} />
          <Route path="/leave" element={<Suspense fallback={<AppLoader/>}><LeaveManagement/></Suspense>} />
          <Route path="/shifts" element={<Suspense fallback={<AppLoader/>}><Shifts/></Suspense>} />
          <Route path="/reports" element={<Suspense fallback={<AppLoader/>}><Reports/></Suspense>} />
        </Route>

        <Route path="*" element={<AuthAwareFallback />} />
      </Routes>
    </>
  )
}
