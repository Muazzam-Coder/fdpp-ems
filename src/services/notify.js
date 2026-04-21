import { toast } from 'sonner'

const RECENT_DUPLICATE_WINDOW = 1500 // ms
const recentMessages = new Map()

function normalizeMessage(input, fallback){
  if(typeof input === 'string' && input.trim()) return input
  if(Array.isArray(input) && input.length){
    return input.map((it)=> normalizeMessage(it, '')).filter(Boolean).join(' ')
  }
  if(input && typeof input === 'object'){
    if(typeof input.message === 'string' && input.message.trim()) return input.message
    if(typeof input.detail === 'string' && input.detail.trim()) return input.detail
    if(Array.isArray(input.non_field_errors) && input.non_field_errors.length){
      return input.non_field_errors.join(' ')
    }

    // Flatten other object shapes: field: [errors]
    const parts = []
    for(const [key, val] of Object.entries(input)){
      if(Array.isArray(val) && val.length){
        parts.push(`${key}: ${val.join(' ')}`)
      }else if(typeof val === 'string' && val.trim()){
        parts.push(`${key}: ${val}`)
      }
    }
    if(parts.length) return parts.join(' ')
  }

  return fallback
}

function shouldShow(message){
  if(!message) return false
  const now = Date.now()
  const prev = recentMessages.get(message)
  if(prev && (now - prev) < RECENT_DUPLICATE_WINDOW) return false
  recentMessages.set(message, now)
  // schedule cleanup
  setTimeout(()=> recentMessages.delete(message), RECENT_DUPLICATE_WINDOW * 2)
  return true
}

export function notifySuccess(message, options = {}){
  const text = normalizeMessage(message, 'Action completed successfully')
  if(!shouldShow(text)) return null
  return toast.success(text, options)
}

export function notifyError(message, options = {}){
  const text = normalizeMessage(message, 'Something went wrong')
  if(!shouldShow(text)) return null
  return toast.error(text, options)
}

export function notifyInfo(message, options = {}){
  const text = normalizeMessage(message, 'Heads up')
  if(!shouldShow(text)) return null
  return toast.info(text, options)
}

export function notifyWarning(message, options = {}){
  const text = normalizeMessage(message, 'Please check this')
  if(!shouldShow(text)) return null
  return toast.warning(text, options)
}
