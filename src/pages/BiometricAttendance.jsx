import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { formatTime12 } from '../utils/dateTime'

const MAX_ACTIVITY_LOGS = 7

function resolveApiOrigin(){
  const configured = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/'
  try{
    return new URL(configured, window.location.origin).origin
  }catch{
    return window.location.origin
  }
}

function resolveAttendanceWsUrl(){
  const configuredSocketUrl = import.meta.env.VITE_ATTENDANCE_WS_URL
  if(configuredSocketUrl) return configuredSocketUrl

  const apiOrigin = resolveApiOrigin()
  try{
    const parsed = new URL(apiOrigin)
    const protocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${parsed.host}/ws/biometric/`
  }catch{
    return 'ws://localhost:8000/ws/biometric/'
  }
}

function toMediaUrl(path, apiOrigin){
  if(!path) return ''
  if(/^https?:\/\//i.test(path)) return path
  const normalized = String(path).startsWith('/') ? path : `/${path}`
  return `${apiOrigin}${normalized}`
}

function prettyStatus(value){
  if(!value) return 'Unknown'
  return String(value)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char)=> char.toUpperCase())
}

function deriveAction(action, lastStatus){
  if(action === 'check_in' || action === 'check_out') return action
  if(String(lastStatus || '').toLowerCase().includes('out')) return 'check_out'
  return 'check_in'
}

function actionLabel(action){
  return action === 'check_out' ? 'Checked Out' : 'Checked In'
}

function safeTime(value){
  if(!value) return '--:--'
  const text = String(value).trim()
  // If server already provided an AM/PM formatted string, use it as-is
  if(/[AP]M$/i.test(text)) return text
  return formatTime12(value)
}

function employeeKey(value){
  const text = String(value ?? '').trim()
  if(!text) return ''

  const numeric = Number(text)
  if(Number.isFinite(numeric)) return String(numeric)
  return text.toLowerCase()
}

function appendRecentActivity(currentList, nextEntry){
  return [nextEntry, ...currentList].slice(0, MAX_ACTIVITY_LOGS)
}

function withActivityLogKey(nextEntry, sequenceNumber, sourceTimestamp){
  const fallbackKey = `emp-${String(nextEntry?.name || 'unknown').toLowerCase().replace(/\s+/g, '-')}`
  const idKey = employeeKey(nextEntry?.emp_id) || fallbackKey
  const rawTimestamp = String(sourceTimestamp || '').trim()
  const timestampPart = rawTimestamp || new Date().toISOString()
  const logKey = `${idKey}-${timestampPart}-${sequenceNumber}`

  return { ...nextEntry, idKey, logKey }
}

export default function BiometricAttendance(){
  const [clockNow, setClockNow] = useState(()=> new Date())
  const [serverNow, setServerNow] = useState(null)
  const [connectionState, setConnectionState] = useState('connecting')
  const [focusEmployee, setFocusEmployee] = useState(null)
  const [recentActivity, setRecentActivity] = useState([])

  const wsRef = useRef(null)
  const initialConnectTimerRef = useRef(null)
  const reconnectTimerRef = useRef(null)
  const keepAliveRef = useRef(true)
  const activityNodesRef = useRef(new Map())
  const previousActivityRectsRef = useRef(new Map())
  const activitySequenceRef = useRef(0)

  const apiOrigin = useMemo(()=> resolveApiOrigin(), [])
  const wsUrl = useMemo(()=> resolveAttendanceWsUrl(), [])

  useEffect(()=>{
    const timer = window.setInterval(()=>{
      setClockNow(new Date())
      // advance server clock by 1s if we have one
      setServerNow((prev)=> prev ? new Date(prev.getTime() + 1000) : prev)
    }, 1000)
    return ()=> window.clearInterval(timer)
  }, [])

  useEffect(()=>{
    keepAliveRef.current = true

    function connectSocket(){
      if(!keepAliveRef.current) return

      const existing = wsRef.current
      if(existing && (existing.readyState === WebSocket.OPEN || existing.readyState === WebSocket.CONNECTING)){
        return
      }

      if(reconnectTimerRef.current){
        window.clearTimeout(reconnectTimerRef.current)
        reconnectTimerRef.current = null
      }

      setConnectionState('connecting')
      const socket = new WebSocket(wsUrl)
      wsRef.current = socket

      socket.onopen = ()=>{
        if(!keepAliveRef.current) return
        setConnectionState('connected')
      }

      socket.onmessage = (event)=>{
        if(!keepAliveRef.current) return

        let payload = null
        try{
          payload = JSON.parse(event.data)
        }catch{
          return
        }

        // Handle errors either as top-level or inside the biometric data
        if(payload?.type === 'error' || payload?.data?.type === 'biometric_error') return

        // Synchronize server time when message contains a timestamp (both connection and attendance)
        try{
          const ts = payload?.timestamp || payload?.data?.timestamp
          if(ts){
            const parsed = new Date(ts)
            if(!Number.isNaN(parsed.getTime())){
              setServerNow(parsed)
            }
          }
        }catch(e){/* ignore */}

        // Accept new `biometric_attendance` messages or legacy `attendance_info`
        if(payload?.type !== 'biometric_attendance' && payload?.type !== 'attendance_info') return

        const data = payload?.type === 'biometric_attendance' ? (payload.data || {}) : payload
        const nextEmployee = {
          emp_id: data.emp_id ?? payload.emp_id ?? '',
          name: data.employee_name || data.name || '-',
          profile_picture: data.profile_img
            ? toMediaUrl(data.profile_img, apiOrigin)
            : (data.profile_picture ? toMediaUrl(data.profile_picture, apiOrigin) : ''),
          shift_type: data.shift_type || '-',
          shift_start: data.shift_start || '',
          shift_end: data.shift_end || '',
          is_late: Boolean(data.is_late),
          message: data.late_message || null,
          last_status: data.last_status || '',
          timestamp: payload.timestamp || data.timestamp || new Date().toISOString(),
          action: data.action ?? null,
          check_in: data.check_in || '',
          check_out: data.check_out || ''
        }

        setFocusEmployee(nextEmployee)

        // Always append a new log entry for each websocket attendance event.
        try{
          // Prefer ISO timestamp from server when available; fall back to provided check times
          const serverTs = (payload.timestamp || data.timestamp || nextEmployee.timestamp)
          const activityTime = nextEmployee.action === 'check_out'
            ? (nextEmployee.check_out || serverTs)
            : (nextEmployee.check_in || serverTs)

          setRecentActivity((currentList)=>{
            const sequenceNumber = ++activitySequenceRef.current
            const nextEntry = withActivityLogKey({
              emp_id: nextEmployee.emp_id,
              name: nextEmployee.name,
              profile_picture: nextEmployee.profile_picture,
              action: deriveAction(nextEmployee.action, nextEmployee.last_status),
              time: safeTime(activityTime),
              check_in: safeTime(nextEmployee.check_in),
              check_out: safeTime(nextEmployee.check_out),
              is_late: nextEmployee.is_late
            }, sequenceNumber, serverTs)

            return appendRecentActivity(currentList, nextEntry)
          })
        }catch(e){
          // ignore any errors updating recentActivity
        }
      }

      socket.onerror = ()=>{
        if(!keepAliveRef.current) return
        setConnectionState('error')
      }

      socket.onclose = ()=>{
        if(wsRef.current === socket){
          wsRef.current = null
        }
        if(!keepAliveRef.current) return
        setConnectionState((current)=> current === 'error' ? 'error' : 'disconnected')
        reconnectTimerRef.current = window.setTimeout(connectSocket, 3200)
      }
    }

    // Defer initial connect by one tick so StrictMode's first effect cleanup cancels it.
    initialConnectTimerRef.current = window.setTimeout(connectSocket, 0)

    return ()=>{
      keepAliveRef.current = false
      if(initialConnectTimerRef.current){
        window.clearTimeout(initialConnectTimerRef.current)
        initialConnectTimerRef.current = null
      }
      if(reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current)
      if(wsRef.current && wsRef.current.readyState < WebSocket.CLOSING){
        wsRef.current.close()
      }
      wsRef.current = null
    }
  }, [apiOrigin, wsUrl])

  const visibleRecentActivity = useMemo(()=>{
    if(!focusEmployee) return recentActivity
    return recentActivity.slice(1)
  }, [focusEmployee, recentActivity])

  useLayoutEffect(()=>{
    const nextRects = new Map()

    visibleRecentActivity.forEach((activity)=>{
      const node = activityNodesRef.current.get(activity.logKey)
      if(!node) return

      const nextRect = node.getBoundingClientRect()
      nextRects.set(activity.logKey, nextRect)

      const previousRect = previousActivityRectsRef.current.get(activity.logKey)
      if(previousRect){
        const deltaY = previousRect.top - nextRect.top
        if(Math.abs(deltaY) > 1){
          node.style.transition = 'none'
          node.style.transform = `translateY(${deltaY}px)`
          node.style.opacity = '0.98'
          node.getBoundingClientRect()
          node.style.transition = 'transform 420ms cubic-bezier(0.22, 1, 0.36, 1), opacity 260ms ease'
          node.style.transform = 'translateY(0)'
          node.style.opacity = '1'
        }
      }else{
        node.classList.remove('biometric-activity-item-enter')
        node.getBoundingClientRect()
        node.classList.add('biometric-activity-item-enter')
      }
    })

    previousActivityRectsRef.current = nextRects
  }, [visibleRecentActivity])

  function bindActivityNode(nodeKey){
    return (node)=>{
      if(!nodeKey) return
      if(node){
        activityNodesRef.current.set(nodeKey, node)
      }else{
        activityNodesRef.current.delete(nodeKey)
      }
    }
  }

  const clockLabel = useMemo(
    ()=> new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(serverNow || clockNow),
    [clockNow, serverNow]
  )

  const connectionLabel = connectionState === 'connected'
    ? 'Connected'
    : connectionState === 'connecting'
      ? 'Connecting'
      : connectionState === 'error'
        ? 'Connection Error'
        : 'Disconnected'

  const activeAction = deriveAction(focusEmployee?.action, focusEmployee?.last_status)

  return (
    <div className="biometric-page">
      <div className="biometric-shell">
        <header className="biometric-topbar">
          <div className="biometric-clock">{clockLabel}</div>

          <div className="biometric-brand" aria-hidden="true">
            <img src="/logo.png" alt="FDPP" className="biometric-logo" />
          </div>

          <div className={`biometric-connection ${connectionState}`}>
            <span className="biometric-connection-dot" aria-hidden="true"></span>
            <span>{connectionLabel}</span>
          </div>
        </header>

        <div className='pt-10'></div>

        <section className="biometric-layout">
          <article className="biometric-activity-panel">
            {/* <p className="biometric-section-caption">Recent Activity</p> */}

            <div className="biometric-activity-list">
              {visibleRecentActivity.length === 0 && (
                <div className="biometric-empty-state">
                  <i className="fa fa-fingerprint" aria-hidden="true"></i>
                  <p>Attendance activity will appear here after the first scan.</p>
                </div>
              )}

              {visibleRecentActivity.map((activity, index)=> (
                <div
                  className={`biometric-activity-item ${index === 0 ? 'is-fresh' : ''} ${activity.action === 'check_out' ? 'status-out' : 'status-in'}`}
                  key={activity.logKey}
                  ref={bindActivityNode(activity.logKey)}
                >
                  <div className="biometric-activity-left">
                    {activity.profile_picture ? (
                      <img src={activity.profile_picture} alt={activity.name} className="biometric-activity-avatar" />
                    ) : (
                      <div className="biometric-activity-avatar placeholder" aria-hidden="true">
                        <i className="fa fa-user"></i>
                      </div>
                    )}

                    <div>
                      <h3>{activity.name}</h3>
                      <p>ID: #{activity.emp_id}</p>
                      <small className="biometric-activity-times">
                        {activity.check_in ? (
                          <>
                            <span className="biometric-activity-time-block"><strong>IN:</strong> {activity.check_in}</span>
                            {activity.action === 'check_out' && (
                              <>
                                <span className="biometric-activity-separator" aria-hidden="true">|</span>
                                <span className="biometric-activity-time-block"><strong>OUT:</strong> {activity.time}</span>
                              </>
                            )}
                          </>
                        ) : (
                          <>{activity.action === 'check_out' ? 'OUT' : 'IN'} {activity.time}</>
                        )}
                      </small>
                    </div>
                  </div>

                  <span className={`biometric-activity-badge ${activity.action === 'check_out' ? 'out' : 'in'}`}>
                    {actionLabel(activity.action)}
                  </span>
                </div>
              ))}
            </div>
          </article>

          <aside className="biometric-profile-card">
            <div className="biometric-profile-avatar-wrap">
              {focusEmployee?.profile_picture ? (
                <img src={focusEmployee.profile_picture} alt={focusEmployee.name || 'Employee profile'} className="biometric-profile-avatar" />
              ) : (
                <div className="biometric-profile-avatar placeholder" aria-hidden="true">
                  <i className="fa fa-user"></i>
                </div>
              )}
            </div>

            <h2>{focusEmployee?.name || 'Awaiting Employee'}</h2>
            <p className="biometric-profile-id">EMP ID: {focusEmployee?.emp_id || '----'}</p>

            <div className={`biometric-profile-status ${activeAction === 'check_out' ? 'out' : 'in'}`}>
              <i className="fa fa-circle" aria-hidden="true"></i>
              <span>{actionLabel(activeAction)}</span>
            </div>

            <div className="biometric-time-grid">
              <div className="biometric-time-box">
                <p>Check In</p>
                <h3>{safeTime(focusEmployee?.check_in)}</h3>
              </div>

              <div className="biometric-time-box">
                <p>Check Out</p>
                <h3>{safeTime(focusEmployee?.check_out)}</h3>
              </div>
            </div>

            <div className="biometric-profile-meta">
              <small>Shift</small>
              <span>{prettyStatus(focusEmployee?.shift_type || '-')}</span>
            </div>

            {/* <div className="biometric-profile-meta">
              <small>Status</small>
              <span>{prettyStatus(focusEmployee?.last_status || '-')}</span>
            </div> */}

            <p
              className={`biometric-late-note ${focusEmployee?.message ? 'is-visible' : 'is-hidden'}`}
              aria-hidden={!focusEmployee?.message}
              aria-live="polite"
            >
              {focusEmployee?.message ?? ''}
            </p>
          </aside>
        </section>
      </div>
    </div>
  )
}