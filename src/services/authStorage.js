const AUTH_STORAGE_KEY = 'fdpp_auth_state'

export const AUTH_CHANGED_EVENT = 'fdpp:auth-changed'
export const AUTH_LOGOUT_EVENT = 'fdpp:auth-logout'

function hasWindow(){
  return typeof window !== 'undefined'
}

function toStringValue(value){
  return typeof value === 'string' ? value : ''
}

function normalizeAuth(value){
  if(!value || typeof value !== 'object'){
    return {
      accessToken: '',
      refreshToken: '',
      username: '',
      role: '',
      userId: '',
      empId: '',
      name: '',
      email: ''
    }
  }

  return {
    accessToken: toStringValue(value.accessToken),
    refreshToken: toStringValue(value.refreshToken),
    username: toStringValue(value.username),
    role: toStringValue(value.role),
    userId: toStringValue(value.userId || value.user_id),
    empId: toStringValue(value.empId || value.emp_id),
    name: toStringValue(value.name),
    email: toStringValue(value.email)
  }
}

function dispatchEvent(eventName, detail){
  if(!hasWindow()) return
  window.dispatchEvent(new CustomEvent(eventName, { detail }))
}

export function readAuthState(){
  if(!hasWindow()) return normalizeAuth(null)

  try{
    const raw = window.localStorage.getItem(AUTH_STORAGE_KEY)
    if(!raw) return normalizeAuth(null)
    return normalizeAuth(JSON.parse(raw))
  }catch{
    return normalizeAuth(null)
  }
}

export function writeAuthState(nextState){
  const normalized = normalizeAuth(nextState)
  if(!hasWindow()) return normalized

  if(normalized.accessToken && normalized.refreshToken){
    window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(normalized))
  }else{
    window.localStorage.removeItem(AUTH_STORAGE_KEY)
  }

  dispatchEvent(AUTH_CHANGED_EVENT, { auth: normalized })
  return normalized
}

export function updateAccessToken(accessToken){
  const current = readAuthState()
  return writeAuthState({ ...current, accessToken: toStringValue(accessToken) })
}

export function clearAuthState(message = ''){
  if(hasWindow()){
    window.localStorage.removeItem(AUTH_STORAGE_KEY)
  }

  const cleared = normalizeAuth(null)
  dispatchEvent(AUTH_CHANGED_EVENT, { auth: cleared })
  dispatchEvent(AUTH_LOGOUT_EVENT, { message })
  return cleared
}

export function isAuthenticatedState(auth){
  return Boolean(auth?.accessToken && auth?.refreshToken)
}

export function decodeJwtPayload(token){
  if(!token || typeof token !== 'string') return null

  try{
    const [, payload] = token.split('.')
    if(!payload) return null

    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    const json = decodeURIComponent(
      atob(base64)
        .split('')
        .map((char)=> `%${`00${char.charCodeAt(0).toString(16)}`.slice(-2)}`)
        .join('')
    )

    return JSON.parse(json)
  }catch{
    return null
  }
}

export function getDisplayName(auth){
  if(auth?.name) return auth.name
  if(auth?.username) return auth.username

  const payload = decodeJwtPayload(auth?.accessToken)
  if(typeof payload?.username === 'string' && payload.username) return payload.username
  if(typeof payload?.user_name === 'string' && payload.user_name) return payload.user_name
  if(typeof payload?.email === 'string' && payload.email) return payload.email
  if(payload?.user_id) return `User ${payload.user_id}`

  return 'Authenticated User'
}
