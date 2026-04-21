function pad2(value){
  return String(value).padStart(2, '0')
}

function extractDateParts(value){
  if(!value) return null
  const text = String(value).trim()
  const isoDateMatch = text.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if(isoDateMatch){
    return {
      year: Number(isoDateMatch[1]),
      month: Number(isoDateMatch[2]),
      day: Number(isoDateMatch[3])
    }
  }

  const parsed = new Date(text)
  if(Number.isNaN(parsed.getTime())) return null
  return {
    year: parsed.getFullYear(),
    month: parsed.getMonth() + 1,
    day: parsed.getDate()
  }
}

function extractTimeParts(value){
  if(!value) return null
  const text = String(value).trim()

  const dateTimeMatch = text.match(/T(\d{1,2}):(\d{2})/)
  if(dateTimeMatch){
    return {
      hour: Number(dateTimeMatch[1]),
      minute: Number(dateTimeMatch[2])
    }
  }

  const timeMatch = text.match(/^(\d{1,2}):(\d{2})/)
  if(timeMatch){
    return {
      hour: Number(timeMatch[1]),
      minute: Number(timeMatch[2])
    }
  }

  const parsed = new Date(text)
  if(Number.isNaN(parsed.getTime())) return null
  return {
    hour: parsed.getHours(),
    minute: parsed.getMinutes()
  }
}

export function formatDate(value){
  const parts = extractDateParts(value)
  if(!parts) return value || '-'
  return `${pad2(parts.day)}/${pad2(parts.month)}/${parts.year}`
}

export function formatTime12(value){
  const parts = extractTimeParts(value)
  if(!parts) return value || '-'

  const hour24 = parts.hour
  const minute = parts.minute
  const suffix = hour24 >= 12 ? 'PM' : 'AM'
  const hour12 = hour24 % 12 || 12
  return `${pad2(hour12)}:${pad2(minute)} ${suffix}`
}

export function formatDateTime(value){
  if(!value) return '-'
  const text = String(value)

  const hasDate = /\d{4}-\d{2}-\d{2}/.test(text)
  const hasTime = /T\d{1,2}:\d{2}/.test(text) || /^\d{1,2}:\d{2}/.test(text)

  if(hasDate && hasTime){
    return `${formatDate(text)} ${formatTime12(text)}`
  }
  if(hasDate) return formatDate(text)
  if(hasTime) return formatTime12(text)
  return text
}

export function formatDateRangeText(value){
  if(!value) return '-'
  return String(value).replace(/(\d{4})-(\d{2})-(\d{2})/g, (_, y, m, d) => `${d}/${m}/${y}`)
}

export function parseISODate(value){
  if(!value) return null
  const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if(match){
    const year = Number(match[1])
    const month = Number(match[2])
    const day = Number(match[3])
    return new Date(year, month - 1, day)
  }

  const parsed = new Date(String(value))
  if(Number.isNaN(parsed.getTime())) return null
  return parsed
}

export function toISODate(value){
  if(!(value instanceof Date) || Number.isNaN(value.getTime())) return ''
  const year = value.getFullYear()
  const month = pad2(value.getMonth() + 1)
  const day = pad2(value.getDate())
  return `${year}-${month}-${day}`
}
