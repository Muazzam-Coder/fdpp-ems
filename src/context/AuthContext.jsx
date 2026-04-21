import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import api from '../services/api'
import {
  AUTH_CHANGED_EVENT,
  AUTH_LOGOUT_EVENT,
  clearAuthState,
  getDisplayName,
  isAuthenticatedState,
  readAuthState,
  writeAuthState
} from '../services/authStorage'

const AuthContext = createContext(null)

export function AuthProvider({ children }){
  const [auth, setAuth] = useState(()=> readAuthState())
  const [ready, setReady] = useState(false)
  const [sessionNotice, setSessionNotice] = useState('')

  useEffect(()=>{
    function onAuthChanged(event){
      if(event?.detail?.auth){
        setAuth(event.detail.auth)
      }else{
        setAuth(readAuthState())
      }
    }

    function onAuthLogout(event){
      const message = event?.detail?.message
      if(message){
        setSessionNotice(message)
      }
      setAuth(readAuthState())
    }

    window.addEventListener(AUTH_CHANGED_EVENT, onAuthChanged)
    window.addEventListener(AUTH_LOGOUT_EVENT, onAuthLogout)
    setReady(true)

    return ()=>{
      window.removeEventListener(AUTH_CHANGED_EVENT, onAuthChanged)
      window.removeEventListener(AUTH_LOGOUT_EVENT, onAuthLogout)
    }
  }, [])

  const login = useCallback(async ({ username, password })=>{
    // Obtain access/refresh tokens first
    const tokenData = await api.obtainToken({ username, password })

    // Try to fetch role / user info (separate endpoint in API v2)
    let userInfo = {}
    try{
      userInfo = await api.authLogin({ username, password })
    }catch(err){
      // If role lookup fails, continue with tokens only
      userInfo = {}
    }

    const next = writeAuthState({
      accessToken: tokenData.access,
      refreshToken: tokenData.refresh,
      username,
      role: userInfo.role || '',
      userId: userInfo.user_id || userInfo.userId || '',
      empId: userInfo.emp_id || userInfo.empId || '',
      name: userInfo.name || userInfo.username || '',
      email: userInfo.email || ''
    })

    setAuth(next)
    setSessionNotice('')
    return { tokenData, userInfo }
  }, [])

  const logout = useCallback((message = '')=>{
    const cleared = clearAuthState(message)
    setAuth(cleared)
  }, [])

  const clearSessionNotice = useCallback(()=> setSessionNotice(''), [])

  const value = useMemo(()=> ({
    ready,
    auth,
    isAuthenticated: isAuthenticatedState(auth),
    displayName: getDisplayName(auth),
    sessionNotice,
    clearSessionNotice,
    login,
    logout
  }), [ready, auth, sessionNotice, clearSessionNotice, login, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(){
  const context = useContext(AuthContext)
  if(!context){
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
