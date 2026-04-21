import React, { useEffect, useState } from 'react'
import api from '../services/api'
import { formatTime12 } from '../utils/dateTime'
import { notifyError, notifySuccess } from '../services/notify'

const defaultShift = {
  name: '',
  start_time: '',
  end_time: '',
  description: ''
}

function toTimeInput(value){
  if(!value) return ''
  const parts = value.split(':')
  if(parts.length < 2) return value
  return `${parts[0]}:${parts[1]}`
}

function toApiTime(value){
  if(!value) return ''
  return value.length === 5 ? `${value}:00` : value
}

export default function Shifts(){
  const [shifts, setShifts] = useState([])
  const [loading, setLoading] = useState(false)

  const [form, setForm] = useState(defaultShift)
  const [editingShift, setEditingShift] = useState(null)

  useEffect(()=>{
    loadShifts()
  }, [])

  async function loadShifts(){
    setLoading(true)
    try{
      const data = await api.getShifts()
      const rows = data.results || data || []
      setShifts(Array.isArray(rows) ? rows : [])
    }catch(requestError){
      notifyError(requestError.message || 'Unable to load shifts')
    }finally{
      setLoading(false)
    }
  }

  function editShift(shift){
    setEditingShift(shift)
    setForm({
      name: shift.name || '',
      start_time: toTimeInput(shift.start_time),
      end_time: toTimeInput(shift.end_time),
      description: shift.description || ''
    })
  }

  function resetForm(){
    setEditingShift(null)
    setForm(defaultShift)
  }

  async function saveShift(event){
    event.preventDefault()
    const payload = {
      ...form,
      start_time: toApiTime(form.start_time),
      end_time: toApiTime(form.end_time)
    }
    try{
      if(editingShift){
        await api.updateShift(editingShift.id, payload)
        notifySuccess('Shift updated successfully')
      }else{
        await api.createShift(payload)
        notifySuccess('Shift created successfully')
      }
      resetForm()
      await loadShifts()
    }catch(requestError){
      notifyError(requestError.message || 'Unable to save shift')
    }
  }

  async function removeShift(shift){
    const allow = window.confirm(`Delete shift ${shift.name}?`)
    if(!allow) return
    try{
      await api.deleteShift(shift.id)
      notifySuccess('Shift deleted successfully')
      await loadShifts()
    }catch(requestError){
      notifyError(requestError.message || 'Unable to delete shift')
    }
  }

  return (
    <div className="space-y-4" style={{ animation: 'rise 0.45s ease both' }}>
      <section className="grid gap-6 md:grid-cols-2">
        <article className="bg-white border border-gray-200 rounded-xl p-6">
          <h2 className="text-xl font-semibold mb-4">{editingShift ? `Edit Shift #${editingShift.id}` : 'Create Shift'}</h2>

          <form className="grid gap-3" onSubmit={saveShift}>
            <label className="grid gap-2 text-sm text-gray-700">
              <span>Shift Name</span>
              <input required value={form.name} onChange={(event)=> setForm({ ...form, name: event.target.value })} className="w-full px-3 py-2 border rounded-lg" />
            </label>

            <label className="grid gap-2 text-sm text-gray-700">
              <span>Start Time</span>
              <input type="time" required value={form.start_time} onChange={(event)=> setForm({ ...form, start_time: event.target.value })} className="w-full px-3 py-2 border rounded-lg" />
            </label>

            <label className="grid gap-2 text-sm text-gray-700">
              <span>End Time</span>
              <input type="time" required value={form.end_time} onChange={(event)=> setForm({ ...form, end_time: event.target.value })} className="w-full px-3 py-2 border rounded-lg" />
            </label>

            <label className="grid gap-2 text-sm text-gray-700">
              <span>Description</span>
              <textarea
                rows="3"
                value={form.description}
                onChange={(event)=> setForm({ ...form, description: event.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
              ></textarea>
            </label>

            <div className="flex justify-end gap-2 mt-2">
              {editingShift && <button type="button" className="px-3 py-2 bg-gray-100 rounded-md" onClick={resetForm}>Cancel Edit</button>}
              <button className="px-4 py-2 bg-emerald-600 text-white rounded-md font-semibold" type="submit">{editingShift ? 'Update Shift' : 'Create Shift'}</button>
            </div>
          </form>
        </article>

        <article className="bg-white border border-gray-200 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Shift Templates</h3>
            <button className="px-3 py-2 bg-gray-100 rounded-md" onClick={loadShifts} disabled={loading}>Refresh</button>
          </div>

          <div className="space-y-3">
            {loading && <p className="text-gray-500">Loading shifts...</p>}
            {!loading && shifts.length === 0 && <p className="text-gray-500">No shifts configured.</p>}
            {!loading && shifts.map((shift)=> (
              <div key={shift.id} className="flex items-start justify-between gap-4 bg-white border border-gray-100 rounded-md p-3">
                <div className="min-w-0">
                  <p className="font-semibold truncate">{shift.name}</p>
                  <small className="text-sm text-gray-600">{formatTime12(shift.start_time)} to {formatTime12(shift.end_time)}</small>
                  {shift.description && <p className="text-sm text-gray-700 mt-1 truncate">{shift.description}</p>}
                </div>
                <div className="flex items-center gap-2">
                  <button className="p-2 rounded-md bg-gray-100 hover:bg-gray-200" onClick={()=> editShift(shift)} title="Edit shift">
                    <i className="fa fa-pen text-sm text-gray-700"></i>
                  </button>
                  <button className="p-2 rounded-md bg-red-50 hover:bg-red-100 text-red-600" onClick={()=> removeShift(shift)} title="Delete shift">
                    <i className="fa fa-trash text-sm"></i>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  )
}
