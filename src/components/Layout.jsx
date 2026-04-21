import React, { useMemo, useState, useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const baseNav = [
  { to: '/', label: 'Dashboard', icon: 'fa-chart-pie' },
  { to: '/employees', label: 'Employees', icon: 'fa-users' },
  { to: '/attendance', label: 'Attendance', icon: 'fa-fingerprint' },
  { to: '/leave', label: 'Leave', icon: 'fa-calendar-check' },
  { to: '/shifts', label: 'Shifts', icon: 'fa-clock' },
  { to: '/reports', label: 'Reports', icon: 'fa-file-invoice' }
]

export default function Layout({ children }){
  const loc = useLocation()
  const { displayName, logout, auth } = useAuth()
  const [open, setOpen] = useState(window.innerWidth > 980)
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 980)

  const pageDescriptions = {
    Dashboard: 'Operational overview and team health',
    Employees: 'Manage employee profiles and shifts',
    Attendance: 'Track daily attendance and reports',
    Leave: 'Create and review leave requests',
    Shifts: 'Define and maintain work shifts',
    Reports: 'Payout and attendance analytics',
    Users: 'Manage roles and access control'
  }

  const items = useMemo(()=> {
    const list = baseNav.slice()
    if(auth?.role === 'admin'){
      list.push({ to: '/users', label: 'Users', icon: 'fa-user-shield' })
    }
    return list
  }, [auth?.role])

  const activePage = useMemo(()=>{
    const item = items.find((entry)=> entry.to === loc.pathname)
    return item ? item.label : 'Employee Management'
  }, [loc.pathname, items])

  const activeDescription = pageDescriptions[activePage] || 'Workforce operations'
  const todayLabel = useMemo(
    ()=> new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' }).format(new Date()),
    []
  )

  useEffect(()=>{
    function onResize(){ setIsMobile(window.innerWidth <= 980) }
    window.addEventListener('resize', onResize)
    return ()=> window.removeEventListener('resize', onResize)
  }, [])

  useEffect(()=>{
    // when switching to mobile view, close the sidebar overlay
    if(isMobile && open){
      setOpen(false)
    }
  }, [isMobile])

  const sidebarClasses = [
    'z-20 flex flex-col gap-3 overflow-x-hidden overflow-y-auto border-r border-white/10 bg-gradient-to-b from-[#0c4d5b] via-[#0a3d4e] to-[#083241] text-[#d9edf2] transition-all duration-200',
    isMobile
      ? `fixed inset-y-0 left-0 w-[min(84vw,300px)] rounded-r-[18px] px-3.5 py-4 ${open ? 'translate-x-0' : '-translate-x-[108%]'}`
      : `${open ? 'sticky top-0 h-screen w-[274px] px-3.5 py-[18px] shadow-[inset_-1px_0_0_rgba(218,238,245,0.1),12px_0_24px_rgba(4,20,32,0.22)]' : 'sticky top-0 h-screen w-[84px] px-2.5 py-3.5 shadow-none'}`
  ].join(' ')

  const navLabelHidden = !open && !isMobile

  return (
    <div className="flex min-h-screen">
      <aside className={sidebarClasses} aria-hidden={isMobile && !open}>
        <div className="mb-1.5">
          <img
            src="/logo.png"
            alt="Fazal Din's Pharma Plus"
            className={`h-auto w-full rounded-[10px] bg-white p-[3px] ${navLabelHidden ? 'hidden' : 'block'}`}
          />
        </div>

        <nav className="mt-2 flex flex-col gap-[5px]" role="navigation">
          {/* <p className="nav-caption">Main Navigation</p> */}
          {items.map((item)=> (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              title={item.label}
              aria-label={item.label}
              className={({ isActive })=> {
                const base = 'group flex min-h-11 items-center rounded-xl border text-[0.95rem] font-semibold transition-all duration-200'
                const spacing = navLabelHidden ? 'justify-center px-1.5 py-2.5' : 'gap-2.5 px-3 py-2.5'
                const tone = isActive
                  ? 'border-[#c0e9e359] bg-[linear-gradient(135deg,rgba(243,255,252,0.2)_0%,rgba(212,241,237,0.16)_100%)] text-white shadow-[inset_3px_0_0_#79d0c6]'
                  : 'border-transparent text-[#d0e6ee] hover:translate-x-[1px] hover:border-[#cceaf02e] hover:bg-white/10'
                return `${base} ${spacing} ${tone}`
              }}
              onClick={()=> { if(isMobile) setOpen(false) }}
            >
              <i
                className={`fa ${item.icon} inline-grid h-7 w-7 place-items-center rounded-[9px] bg-white/10 ${navLabelHidden ? 'text-base' : ''}`}
                aria-hidden="true"
              ></i>
              <span className={navLabelHidden ? 'hidden' : ''}>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className={`mt-auto border-t border-white/15 px-2.5 pb-0.5 pt-2.5 ${navLabelHidden ? 'border-t-0 px-0 pt-0' : ''}`}>
          <small className={`text-[0.72rem] uppercase tracking-[0.08em] text-[#daeff4a3] ${navLabelHidden ? 'hidden' : 'block'}`}>
            {auth?.role ? `${auth.role} access` : 'team access'}
          </small>
        </div>
      </aside>

      {isMobile && open && (
        <button
          className="fixed inset-0 z-[18] border-0 bg-[rgba(8,17,30,0.35)]"
          onClick={()=> setOpen(false)}
          aria-label="Close menu"
        />
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-2 z-10 mx-4 mt-2.5 flex items-center justify-between rounded-2xl border border-[rgba(196,211,220,0.85)] bg-[linear-gradient(180deg,rgba(252,254,255,0.95)_0%,rgba(246,251,252,0.9)_100%)] px-[18px] py-[14px] shadow-[0_10px_24px_rgba(18,35,49,0.08)] backdrop-blur-[12px] max-[980px]:mx-2.5 max-[980px]:mt-2 max-[980px]:top-1.5 max-[980px]:px-3 max-[980px]:py-3">
          <div className="flex items-center gap-3">
            <button
              className="inline-grid h-10 w-10 place-items-center rounded-[13px] border border-[var(--line)] bg-[#f7fbfd] text-[var(--text)] shadow-[inset_0_1px_0_rgba(255,255,255,0.75)]"
              onClick={()=> setOpen((old)=> !old)}
              aria-label="Toggle menu"
              aria-expanded={open ? 'true' : 'false'}
            >
              <i className={`fa ${open && isMobile ? 'fa-times' : 'fa-bars'}`}></i>
            </button>
            <div className="grid gap-0.5">
              <h1 className="m-0 font-[Space_Grotesk,Sora,sans-serif] text-[1.42rem] max-[720px]:text-[1.15rem]">{activePage}</h1>
              <p className="m-0 text-xs text-[var(--muted)] max-[720px]:hidden">{activeDescription}</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div
              className="rounded-full border border-[rgba(196,212,221,0.95)] bg-[#edf5f8] px-[11px] py-2 text-[0.78rem] font-semibold text-[#425565] max-[980px]:hidden"
              aria-label="Current date"
            >
              {todayLabel}
            </div>
            <div
              className="inline-flex max-w-[min(40vw,320px)] items-center gap-[7px] rounded-full border border-[rgba(185,202,212,0.8)] bg-white px-[10px] py-[7px] text-[0.82rem] text-[var(--text)] max-[980px]:max-w-[52vw]"
              title={displayName}
            >
              <i className="fa fa-user-circle" aria-hidden="true"></i>
              <div className="grid leading-[1.1]">
                <span className="overflow-hidden text-ellipsis whitespace-nowrap max-[720px]:hidden">{displayName}</span>
                {auth?.role && (
                  <small className="text-[0.68rem] uppercase tracking-[0.08em] text-[rgba(84,102,117,0.8)] max-[720px]:hidden">
                    {auth.role}
                  </small>
                )}
              </div>
            </div>
            <button
              className="inline-flex items-center gap-1.5 rounded-[11px] border border-[var(--line)] bg-white px-[13px] py-[9px] font-[Space_Grotesk,Sora,sans-serif] text-[0.85rem] font-semibold text-[var(--text)] transition hover:-translate-y-px hover:brightness-[1.02] max-[720px]:px-[9px]"
              type="button"
              onClick={()=> logout()}
            >
              <i className="fa fa-right-from-bracket" aria-hidden="true"></i>
              <span className="max-[720px]:hidden">Logout</span>
            </button>
          </div>
        </header>

        <main className="w-full px-[22px] pb-5 pt-4 max-[980px]:px-3 max-[980px]:pb-4 max-[980px]:pt-3.5">{children}</main>
      </div>
    </div>
  )
}
