import React from 'react'
import { createPortal } from 'react-dom'
import DatePicker from 'react-datepicker'
import { parseISODate, toISODate } from '../utils/dateTime'

function PopperContainer({ children }){
  return createPortal(children, typeof document !== 'undefined' ? document.body : document)
}

export default function DatePickerField({
  value,
  onChange,
  placeholder = 'dd/mm/yyyy',
  className = '',
  ...rest
}){
  return (
    <DatePicker
      selected={parseISODate(value)}
      onChange={(date)=> onChange(toISODate(date))}
      dateFormat="dd/MM/yyyy"
      placeholderText={placeholder}
      className={className}
      popperContainer={PopperContainer}
      popperPlacement={rest.popperPlacement || 'bottom-start'}
      popperProps={{
        strategy: 'fixed',
        modifiers: [
          { name: 'preventOverflow', options: { boundary: typeof document !== 'undefined' ? document.body : undefined } },
          { name: 'offset', options: { offset: [0, 8] } }
        ]
      }}
      {...rest}
    />
  )
}
