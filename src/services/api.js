import axios from 'axios'
import { clearAuthState, readAuthState, writeAuthState } from './authStorage'
import { notifyError } from './notify'

function normalizeBaseURL(url){
  if(!url) return 'http://localhost:8000/api/'
  return url.endsWith('/') ? url : `${url}/`
}

const client = axios.create({
  baseURL: normalizeBaseURL(import.meta.env.VITE_API_URL || 'http://localhost:8000/api/'),
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' }
})

let refreshPromise = null

client.interceptors.request.use((config)=>{
  if(!config.skipAuth){
    const auth = readAuthState()
    if(auth.accessToken){
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${auth.accessToken}`
    }
  }
  return config
})

async function refreshAccessToken(){
  if(refreshPromise) return refreshPromise

  const auth = readAuthState()
  if(!auth.refreshToken){
    clearAuthState('Session expired. Please sign in again.')
    throw new Error('Session expired. Please sign in again.')
  }

  refreshPromise = client
    .post('token/refresh/', { refresh: auth.refreshToken }, { skipAuth: true })
    .then((response)=>{
      const nextAccessToken = response.data?.access
      const rotatedRefreshToken = response.data?.refresh
      if(!nextAccessToken){
        throw new Error('Refresh token did not return a new access token')
      }

      const current = readAuthState()
      writeAuthState({
        ...current,
        accessToken: nextAccessToken,
        refreshToken: typeof rotatedRefreshToken === 'string' && rotatedRefreshToken
          ? rotatedRefreshToken
          : current.refreshToken
      })

      return nextAccessToken
    })
    .catch((error)=>{
      clearAuthState('Session expired. Please sign in again.')
      throw error
    })
    .finally(()=>{
      refreshPromise = null
    })

  return refreshPromise
}

client.interceptors.response.use(
  (response)=> response,
  async (error)=>{
    if(!axios.isAxiosError(error)){
      return Promise.reject(error)
    }

    const originalRequest = error.config || {}
    const status = error.response?.status
    const requestUrl = String(originalRequest.url || '')
    const isRefreshRequest = requestUrl.includes('token/refresh/')

    if(status === 401 && !originalRequest.skipAuth && !originalRequest._retry && !isRefreshRequest){
      originalRequest._retry = true
      try{
        const nextAccessToken = await refreshAccessToken()
        originalRequest.headers = originalRequest.headers || {}
        originalRequest.headers.Authorization = `Bearer ${nextAccessToken}`
        return client(originalRequest)
      }catch(refreshError){
        return Promise.reject(refreshError)
      }
    }

    // For non-401 errors, show backend-provided message as a toast.
    try{
      const extracted = extractErrorMessage(error.response?.data) || error.message || 'Request failed'
      if(status && status !== 401){
        notifyError(extracted)
      }
    }catch(_){
      // ignore notification errors
    }

    return Promise.reject(error)
  }
)

function extractErrorMessage(data){
  if(data == null) return null

  if(typeof data === 'string') return data

  if(Array.isArray(data)){
    const parts = data.map((it)=> extractErrorMessage(it)).filter(Boolean)
    return parts.join(' ')
  }

  if(typeof data === 'object'){
    if(typeof data.error === 'string') return data.error
    if(typeof data.detail === 'string') return data.detail
    if(typeof data.message === 'string') return data.message

    if(Array.isArray(data.non_field_errors) && data.non_field_errors.length){
      return data.non_field_errors.join(' ')
    }

    const parts = []
    for(const [key, val] of Object.entries(data)){
      if(Array.isArray(val) && val.length){
        const joined = val.map((it)=> extractErrorMessage(it)).filter(Boolean).join(' ')
        if(joined) parts.push(joined)
      }else if(typeof val === 'string' && val.trim()){
        parts.push(val)
      }else if(typeof val === 'object' && val !== null){
        const nested = extractErrorMessage(val)
        if(nested) parts.push(nested)
      }
    }

    if(parts.length) return parts.join(' ')
  }

  return null
}

function normalizeError(error){
  if(!axios.isAxiosError(error)){
    const message = error instanceof Error ? error.message : 'Unexpected error'
    return { status: null, message, data: null }
  }
  const status = error.response?.status || null
  const data = error.response?.data || null
  const message = extractErrorMessage(data) || error.message || 'Request failed'
  return { status, message, data }
}

async function request(promise){
  try{
    const response = await promise
    return response.data
  }catch(error){
    throw normalizeError(error)
  }
}

const api = {
  obtainToken(payload){
    return request(client.post('token/', payload, { skipAuth: true }))
  },
  refreshToken(payload){
    return request(client.post('token/refresh/', payload, { skipAuth: true }))
  },
  authLogin(payload){
    // returns role and user info (no token required by docs)
    return request(client.post('auth/login/', payload, { skipAuth: true }))
  },
  authRegister(payload){
    const config = payload instanceof FormData ? { skipAuth: true, headers: { 'Content-Type': 'multipart/form-data' } } : { skipAuth: true }
    return request(client.post('auth/register/', payload, config))
  },
  createAdminManager(payload){
    const config = payload instanceof FormData ? { headers: { 'Content-Type': 'multipart/form-data' } } : undefined
    return request(client.post('auth/create_admin_manager/', payload, config))
  },

  // Access level endpoints (admin-only)
  getAccessLevels(params){
    return request(client.get('access-levels/', { params }))
  },
  createAccessLevel(payload){
    return request(client.post('access-levels/', payload))
  },
  getAccessLevel(id){
    return request(client.get(`access-levels/${id}/`))
  },
  updateAccessLevel(id, payload){
    const config = payload instanceof FormData ? { headers: { 'Content-Type': 'multipart/form-data' } } : undefined
    return request(client.put(`access-levels/${id}/`, payload, config))
  },
  deleteAccessLevel(id){
    return request(client.delete(`access-levels/${id}/`))
  },
  getAdmins(){
    return request(client.get('access-levels/admins/'))
  },
  getManagers(){
    return request(client.get('access-levels/managers/'))
  },

  getEmployees(params){
    return request(client.get('employees/', { params }))
  },
  getEmployee(empId){
    return request(client.get(`employees/${empId}/`))
  },
  createEmployee(payload){
    const config = payload instanceof FormData ? { headers: { 'Content-Type': 'multipart/form-data' } } : undefined
    return request(client.post('employees/', payload, config))
  },
  updateEmployee(empId, payload){
    const config = payload instanceof FormData ? { headers: { 'Content-Type': 'multipart/form-data' } } : undefined
    return request(client.put(`employees/${empId}/`, payload, config))
  },
  patchEmployee(empId, payload){
    return request(client.patch(`employees/${empId}/`, payload))
  },
  deleteEmployee(empId){
    return request(client.delete(`employees/${empId}/`))
  },
  getActiveEmployees(){
    return request(client.get('employees/active_employees/'))
  },
  getEmployeeStats(){
    return request(client.get('employees/employee_stats/'))
  },
  calculatePayout(empId, params){
    return request(client.get(`employees/${empId}/calculate_payout/`, { params }))
  },
  getEmployeeAttendanceReport(empId, params){
    return request(client.get(`employees/${empId}/attendance_report/`, { params }))
  },

  getAttendance(params){
    return request(client.get('attendance/', { params }))
  },
  createAttendance(payload){
    return request(client.post('attendance/', payload))
  },
  checkIn(empId){
    return request(client.post('attendance/check_in/', { emp_id: empId }, { skipAuth: true }))
  },
  checkOut(empId){
    return request(client.post('attendance/check_out/', { emp_id: empId }, { skipAuth: true }))
  },
  autoAttendance(empId){
    return request(client.post('attendance/auto_attendance/', { emp_id: empId }, { skipAuth: true }))
  },
  getDailyReport(params){
    return request(client.get('attendance/daily_report/', { params }))
  },
  getWeeklyReport(){
    return request(client.get('attendance/weekly_report/'))
  },
  getMonthlyReport(params){
    return request(client.get('attendance/monthly_report/', { params }))
  },

  getLeaves(params){
    return request(client.get('leave/', { params }))
  },
  createLeave(payload){
    return request(client.post('leave/', payload))
  },
  getPendingApprovals(){
    return request(client.get('leave/pending_approvals/'))
  },
  approveLeave(leaveId, payload){
    return request(client.post(`leave/${leaveId}/approve/`, payload))
  },
  rejectLeave(leaveId, payload){
    return request(client.post(`leave/${leaveId}/reject/`, payload))
  },
  getEmployeeLeaves(params){
    return request(client.get('leave/employee_leaves/', { params }))
  },

  getShifts(){
    return request(client.get('shifts/'))
  },
  createShift(payload){
    return request(client.post('shifts/', payload))
  },
  updateShift(shiftId, payload){
    return request(client.put(`shifts/${shiftId}/`, payload))
  },
  patchShift(shiftId, payload){
    return request(client.patch(`shifts/${shiftId}/`, payload))
  },
  deleteShift(shiftId){
    return request(client.delete(`shifts/${shiftId}/`))
  }
}

export default api
