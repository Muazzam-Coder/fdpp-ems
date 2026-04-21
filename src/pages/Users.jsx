import React, { useEffect, useState, useRef } from 'react'
import PortalModal from '../components/PortalModal'
import api from '../services/api'
import UsersTable from '../components/UsersTable'
import { notifyError, notifySuccess } from '../services/notify'

const adminManagerDefaults = {
  username: '',
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  role: 'manager',
  profile_img: null,
  remove_image: false
}

const registerDefaults = {
  username: '',
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  address: '',
  relative: '',
  r_phone: '',
  r_address: '',
  profile_img: null,
  remove_image: false,
  start_time: '09:00',
  end_time: '17:00'
}



function toApiTime(value){
  if(!value) return ''
  return value.length === 5 ? `${value}:00` : value
}

function formatPhone(value){
  if(value == null) return ''
  const digits = String(value).replace(/\D/g, '')
  if(digits.length <= 4) return digits
  const first = digits.slice(0,4)
  const rest = digits.slice(4)
  return rest ? `${first}-${rest}` : first
}


export default function Users(){
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [totalCount, setTotalCount] = useState(0)
  const [filter, setFilter] = useState('all')
  const [editingRoles, setEditingRoles] = useState({})
  const [savingRoles, setSavingRoles] = useState({})
  const [rowErrors, setRowErrors] = useState({})

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createMode, setCreateMode] = useState('admin-manager')
  const [adminManagerForm, setAdminManagerForm] = useState(adminManagerDefaults)
  const [registerForm, setRegisterForm] = useState(registerDefaults)
  const [createBusy, setCreateBusy] = useState(false)
  const [createError, setCreateError] = useState('')
  const [createSuccess, setCreateSuccess] = useState('')
  const [showAdminPassword, setShowAdminPassword] = useState(false)
  const [showRegisterPassword, setShowRegisterPassword] = useState(false)
  const [lastRoleChange, setLastRoleChange] = useState(null)
  const modalFileInputRef = useRef(null)
  const [modalPreviewUrl, setModalPreviewUrl] = useState('')
  // Edit user modal state
  const [editingUser, setEditingUser] = useState(null)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editForm, setEditForm] = useState({})
  const editFileInputRef = useRef(null)
  const [editPreviewUrl, setEditPreviewUrl] = useState('')
  const [editBusy, setEditBusy] = useState(false)
  const [editError, setEditError] = useState('')

  useEffect(()=>{ loadUsers() }, [filter])

  useEffect(()=>{
    const form = createMode === 'admin-manager' ? adminManagerForm : registerForm
    // create preview URL when a File is selected
    if(form.profile_img && form.profile_img instanceof File){
      const url = URL.createObjectURL(form.profile_img)
      setModalPreviewUrl(url)
      return ()=> URL.revokeObjectURL(url)
    }
    // if profile_img is a string (existing URL), use it
    if(form.profile_img && typeof form.profile_img === 'string'){
      setModalPreviewUrl(form.profile_img)
      return
    }
    setModalPreviewUrl('')
  }, [createMode, adminManagerForm.profile_img, registerForm.profile_img])

  useEffect(()=>{
    if(!showEditModal) return
    if(!editForm) return
    if(editForm.profile_img && editForm.profile_img instanceof File){
      const url = URL.createObjectURL(editForm.profile_img)
      setEditPreviewUrl(url)
      return ()=> URL.revokeObjectURL(url)
    }
    if(editForm.profile_img && typeof editForm.profile_img === 'string'){
      setEditPreviewUrl(editForm.profile_img)
      return
    }
    setEditPreviewUrl('')
  }, [showEditModal, editForm && editForm.profile_img])

  useEffect(()=>{
    if(error) notifyError(error)
  }, [error])

  useEffect(()=>{
    if(createError) notifyError(createError)
  }, [createError])

  useEffect(()=>{
    if(createSuccess) notifySuccess(createSuccess)
  }, [createSuccess])

  useEffect(()=>{
    if(editError) notifyError(editError)
  }, [editError])

  async function loadUsers(){
    setLoading(true)
    setError('')
    try{
      let data
      if(filter === 'admins'){
        data = await api.getAdmins()
      }else if(filter === 'managers'){
        data = await api.getManagers()
      }else{
        data = await api.getAccessLevels()
      }
      const rows = data.results || data || []
      setUsers(Array.isArray(rows) ? rows : [])
      setTotalCount(data.count || (Array.isArray(rows) ? rows.length : 0))
    }catch(err){
      setError(err.message || 'Unable to load users')
    }finally{
      setLoading(false)
    }
  }

  function beginEditRole(id, currentRole){
    setEditingRoles(prev => ({ ...prev, [id]: currentRole }))
    setRowErrors(prev => ({ ...prev, [id]: '' }))
  }

  function cancelEditRole(id){
    setEditingRoles(prev => {
      const copy = { ...prev }
      delete copy[id]
      return copy
    })
  }

  function changeRoleLocal(id, value){
    setEditingRoles(prev => ({ ...prev, [id]: value }))
  }

  function handleModalAvatarClick(){
    if(modalFileInputRef.current) modalFileInputRef.current.click()
  }

  function handleModalFileChange(event){
    const file = event.target.files && event.target.files[0] ? event.target.files[0] : null
    if(createMode === 'admin-manager'){
      setAdminManagerForm(prev => ({ ...prev, profile_img: file, remove_image: false }))
    }else{
      setRegisterForm(prev => ({ ...prev, profile_img: file, remove_image: false }))
    }
  }

  function handleModalDrop(event){
    event.preventDefault()
    const file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0] ? event.dataTransfer.files[0] : null
    if(!file) return
    if(createMode === 'admin-manager'){
      setAdminManagerForm(prev => ({ ...prev, profile_img: file, remove_image: false }))
    }else{
      setRegisterForm(prev => ({ ...prev, profile_img: file, remove_image: false }))
    }
  }

  function handleModalDragOver(event){
    event.preventDefault()
  }

  function handleModalRemoveImage(){
    if(createMode === 'admin-manager'){
      setAdminManagerForm(prev => ({ ...prev, profile_img: null, remove_image: true }))
    }else{
      setRegisterForm(prev => ({ ...prev, profile_img: null, remove_image: true }))
    }
    setModalPreviewUrl('')
  }

  async function saveRole(id){
    const nextRole = editingRoles[id]
    if(!nextRole) return
    setSavingRoles(prev => ({ ...prev, [id]: true }))
    setRowErrors(prev => ({ ...prev, [id]: '' }))
    const prevRole = users.find(u=>u.id === id)?.role
    // Optimistic update
    setUsers(prev => prev.map(u => (u.id === id ? { ...u, role: nextRole } : u)))
    try{
      await api.updateAccessLevel(id, { role: nextRole })
      cancelEditRole(id)
      notifySuccess('User role updated successfully')
      // set undo state (clear any previous timer)
      if(lastRoleChange && lastRoleChange.timerId){
        clearTimeout(lastRoleChange.timerId)
      }
      const timerId = setTimeout(()=> setLastRoleChange(null), 6000)
      setLastRoleChange({ id, prevRole, timerId })
    }catch(err){
      // revert on error
      setUsers(prev => prev.map(u => (u.id === id ? { ...u, role: prevRole } : u)))
      const msg = err.message || 'Unable to update role'
      setRowErrors(prev => ({ ...prev, [id]: msg }))
      notifyError(msg)
    }finally{
      setSavingRoles(prev => ({ ...prev, [id]: false }))
    }
  }

  async function undoRole(id){
    if(!lastRoleChange || lastRoleChange.id !== id) return
    const prevRole = lastRoleChange.prevRole
    setSavingRoles(prev => ({ ...prev, [id]: true }))
    setRowErrors(prev => ({ ...prev, [id]: '' }))
    try{
      await api.updateAccessLevel(id, { role: prevRole })
      setUsers(prev => prev.map(u => (u.id === id ? { ...u, role: prevRole } : u)))
      notifySuccess('Role change reverted')
      if(lastRoleChange.timerId) clearTimeout(lastRoleChange.timerId)
      setLastRoleChange(null)
    }catch(err){
      const msg = err.message || 'Unable to revert role'
      setRowErrors(prev => ({ ...prev, [id]: msg }))
      notifyError(msg)
    }finally{
      setSavingRoles(prev => ({ ...prev, [id]: false }))
    }
  }

  function getInitials(u){
    const name = (u.username || u.user || u.name || '').trim()
    if(!name) return '?'
    const parts = name.split(/\s+/).filter(Boolean)
    if(parts.length === 1) return parts[0].slice(0,2).toUpperCase()
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }

  async function removeAccessLevel(record){
    if(!record?.id) return
    const ok = window.confirm(`Remove access level for ${record.username || `ID ${record.id}`}?`)
    if(!ok) return
    setRowErrors(prev => ({ ...prev, [record.id]: '' }))
    try{
      await api.deleteAccessLevel(record.id)
      notifySuccess('Access level removed successfully')
      await loadUsers()
    }catch(err){
      const msg = err.message || 'Unable to remove access level'
      setRowErrors(prev => ({ ...prev, [record.id]: msg }))
      notifyError(msg)
    }
  }

  function openEditUser(user){
    if(!user) return
    setEditError('')
    setEditingUser(user)
    const f = {
      username: user.username || '',
      email: user.email || '',
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      role: user.role || 'employee',
      relative: user.relative || '',
      r_phone: formatPhone(user.r_phone || ''),
      r_address: user.r_address || '',
      start_time: user.start_time ? user.start_time.slice(0,5) : '09:00',
      end_time: user.end_time ? user.end_time.slice(0,5) : '17:00',
      profile_img: user.profile_img || null,
      remove_image: false
    }
    setEditForm(f)
    setShowEditModal(true)
  }

  function closeEditModal(){
    setShowEditModal(false)
    setEditingUser(null)
    setEditForm({})
    setEditPreviewUrl('')
  }

  function handleEditAvatarClick(){
    if(editFileInputRef.current) editFileInputRef.current.click()
  }

  function handleEditFileChange(event){
    const file = event.target.files && event.target.files[0] ? event.target.files[0] : null
    setEditForm(prev => ({ ...prev, profile_img: file, remove_image: false }))
  }

  function handleEditDrop(event){
    event.preventDefault()
    const file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0] ? event.dataTransfer.files[0] : null
    if(!file) return
    setEditForm(prev => ({ ...prev, profile_img: file, remove_image: false }))
  }

  function handleEditDragOver(event){
    event.preventDefault()
  }

  function handleEditRemoveImage(){
    setEditForm(prev => ({ ...prev, profile_img: null, remove_image: true }))
    setEditPreviewUrl('')
  }

  async function submitEditUser(event){
    event.preventDefault()
    if(!editingUser || !editingUser.id) return
    setEditBusy(true)
    setEditError('')
    try{
      const f = editForm
      const hasFile = f.profile_img && f.profile_img instanceof File
      const removed = !!f.remove_image
      let data
      if(hasFile || removed){
        const fd = new FormData()
        fd.append('username', f.username.trim())
        fd.append('email', f.email.trim())
        fd.append('first_name', f.first_name.trim())
        fd.append('last_name', f.last_name.trim())
        fd.append('role', f.role)
        
        if(f.address) fd.append('address', f.address.trim())
        if(f.relative) fd.append('relative', f.relative.trim())
        if(f.r_phone) fd.append('r_phone', f.r_phone.trim())
        if(f.r_address) fd.append('r_address', f.r_address.trim())
        if(f.start_time) fd.append('start_time', toApiTime(f.start_time))
        if(f.end_time) fd.append('end_time', toApiTime(f.end_time))
        if(hasFile) fd.append('profile_img', f.profile_img)
        if(removed){ fd.append('profile_img', ''); fd.append('remove_profile_img', '1') }
        data = await api.updateAccessLevel(editingUser.id, fd)
      }else{
        data = await api.updateAccessLevel(editingUser.id, {
          username: f.username.trim(),
          email: f.email.trim(),
          first_name: f.first_name.trim(),
          last_name: f.last_name.trim(),
          role: f.role,
          address: f.address.trim(),
          relative: f.relative.trim(),
          r_phone: f.r_phone.trim(),
          r_address: f.r_address.trim(),
          start_time: toApiTime(f.start_time),
          end_time: toApiTime(f.end_time)
        })
      }

      notifySuccess(data?.message || 'User updated successfully')
      await loadUsers()
      closeEditModal()
    }catch(err){
      setEditError(err.message || 'Unable to update user')
    }finally{
      setEditBusy(false)
    }
  }

  function openCreateModal(){
    setCreateError('')
    setCreateSuccess('')
    setShowCreateModal(true)
  }

  function closeCreateModal(){
    setShowCreateModal(false)
  }

  async function submitCreateUser(event){
    event.preventDefault()
    setCreateBusy(true)
    setCreateError('')
    setCreateSuccess('')

    try{
      let data

      if(createMode === 'admin-manager'){
        const f = adminManagerForm
        const hasFile = f.profile_img && f.profile_img instanceof File
        const removed = !!f.remove_image
        if(hasFile || removed){
          const fd = new FormData()
          fd.append('username', f.username.trim())
          fd.append('email', f.email.trim())
          fd.append('password', f.password)
          fd.append('first_name', f.first_name.trim())
          fd.append('last_name', f.last_name.trim())
          fd.append('role', f.role)
          
          if(hasFile) fd.append('profile_img', f.profile_img)
          if(removed){ fd.append('profile_img', ''); fd.append('remove_profile_img', '1') }
          data = await api.createAdminManager(fd)
        }else{
          data = await api.createAdminManager({
            username: f.username.trim(),
            email: f.email.trim(),
            password: f.password,
            first_name: f.first_name.trim(),
            last_name: f.last_name.trim(),
            role: f.role,
            
          })
        }
      }else{
        const f = registerForm
        const hasFile = f.profile_img && f.profile_img instanceof File
        const removed = !!f.remove_image
        if(hasFile || removed){
          const fd = new FormData()
          fd.append('username', f.username.trim())
          fd.append('email', f.email.trim())
          fd.append('password', f.password)
          fd.append('first_name', f.first_name.trim())
          fd.append('last_name', f.last_name.trim())
        
          fd.append('address', f.address.trim())
          fd.append('relative', f.relative.trim())
          fd.append('r_phone', f.r_phone.trim())
          fd.append('r_address', f.r_address.trim())
          fd.append('start_time', toApiTime(f.start_time))
          fd.append('end_time', toApiTime(f.end_time))
          if(hasFile) fd.append('profile_img', f.profile_img)
          if(removed){ fd.append('profile_img', ''); fd.append('remove_profile_img', '1') }
          data = await api.authRegister(fd)
        }else{
          data = await api.authRegister({
            username: f.username.trim(),
            email: f.email.trim(),
            password: f.password,
            first_name: f.first_name.trim(),
            last_name: f.last_name.trim(),
            address: f.address.trim(),
            relative: f.relative.trim(),
            r_phone: f.r_phone.trim(),
            r_address: f.r_address.trim(),
            start_time: toApiTime(f.start_time),
            end_time: toApiTime(f.end_time)
          })
        }
      }

      setCreateSuccess(data?.message || 'User created successfully')
      setAdminManagerForm(adminManagerDefaults)
      setRegisterForm(registerDefaults)
      setModalPreviewUrl('')
      await loadUsers()
      setShowCreateModal(false)
    }catch(err){
      setCreateError(err.message || 'Unable to create user')
    }finally{
      setCreateBusy(false)
    }
  }

  useEffect(() => {
    const originalOverflow = document.body.style.overflow;
    if (showCreateModal || showEditModal) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = originalOverflow;
    }
    return () => { document.body.style.overflow = originalOverflow; };
  }, [showCreateModal, showEditModal]);

  const inputBase = 'w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100'
  const labelBase = 'flex flex-col gap-1 text-sm font-medium text-slate-600'
  const primaryBtn = 'inline-flex items-center justify-center rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-60'
  const secondaryBtn = 'inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60'
  const iconBtn = 'inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-700 transition hover:bg-slate-100'

  return (
    <div className="space-y-4" style={{ animation: 'rise 0.45s ease both' }}>
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-slate-500">{totalCount} records</p>
          <div className="flex flex-wrap items-center gap-2">
            <button className={primaryBtn} type="button" onClick={openCreateModal}>
              <i className="fa fa-user-plus mr-2"></i>
              New User
            </button>
            <button
              className={filter === 'all' ? primaryBtn : secondaryBtn}
              type="button"
              onClick={()=> setFilter('all')}
            >
              All
            </button>
            <button
              className={filter === 'admins' ? primaryBtn : secondaryBtn}
              type="button"
              onClick={()=> setFilter('admins')}
            >
              Admins
            </button>
            <button
              className={filter === 'managers' ? primaryBtn : secondaryBtn}
              type="button"
              onClick={()=> setFilter('managers')}
            >
              Managers
            </button>
            <button className={secondaryBtn} type="button" onClick={loadUsers} disabled={loading}>
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>

        <UsersTable
          users={users}
          loading={loading}
          editingRoles={editingRoles}
          savingRoles={savingRoles}
          rowErrors={rowErrors}
          beginEditRole={beginEditRole}
          cancelEditRole={cancelEditRole}
          changeRoleLocal={changeRoleLocal}
          saveRole={saveRole}
          removeAccessLevel={removeAccessLevel}
          openEditUser={openEditUser}
          lastRoleChange={lastRoleChange}
          undoRole={undoRole}
          getInitials={getInitials}
        />
      </section>

      <PortalModal
        open={showCreateModal}
        onClose={closeCreateModal}
        overlayClassName="fixed inset-0 z-[70] flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm"
        innerClassName="w-full flex items-center justify-center px-4 md:px-0"
      >
        <div className="max-h-[92vh] w-full max-w-5xl overflow-auto rounded-2xl border border-slate-200 bg-white p-5 shadow-2xl relative">
          {createBusy && (
            <div className="absolute inset-0 z-10 bg-white/70 p-6 flex flex-col gap-3">
              <div className="skeleton h-6 w-40 rounded"></div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="skeleton h-10 w-full rounded"></div>
                <div className="skeleton h-10 w-full rounded"></div>
                <div className="skeleton h-10 w-full rounded"></div>
                <div className="skeleton h-10 w-full rounded"></div>
              </div>
              <div className="skeleton h-10 w-32 rounded mt-2"></div>
            </div>
          )}
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-xl font-semibold text-slate-800">Create User</h3>
              <button className={iconBtn} type="button" onClick={closeCreateModal}>
                <i className="fa fa-times"></i>
              </button>
            </div>

            <div className="mb-5 flex flex-col items-center justify-center gap-2">
              <input
                ref={modalFileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleModalFileChange}
              />

              <div
                className="group relative flex h-32 w-32 cursor-pointer items-center justify-center overflow-hidden rounded-full border-2 border-dashed border-teal-300 bg-teal-50 transition hover:border-teal-500"
                onClick={handleModalAvatarClick}
                onDrop={handleModalDrop}
                onDragOver={handleModalDragOver}
                onKeyDown={(e)=> {
                  if(e.key === 'Enter' || e.key === ' ') handleModalAvatarClick()
                }}
                role="button"
                tabIndex={0}
              >
                {modalPreviewUrl ? (
                  <>
                    <img src={modalPreviewUrl} alt="avatar preview" className="h-full w-full object-cover" />
                    <button
                      type="button"
                      className="absolute right-1 top-1 inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white/95 text-rose-600 shadow"
                      onClick={handleModalRemoveImage}
                      aria-label="Remove image"
                    >
                      <i className="fa fa-trash"></i>
                    </button>
                  </>
                ) : (
                  <i className="fa fa-cloud-upload-alt text-3xl text-teal-600"></i>
                )}
                <span className="sr-only">Click or drop an image</span>
              </div>
              <p className="text-xs text-slate-500">Click or drag an image</p>
            </div>

            <form className="grid grid-cols-1 gap-3 md:grid-cols-2" onSubmit={submitCreateUser}>
              {createMode === 'admin-manager' ? (
                <>
                  <label className={labelBase}>
                    Username
                    <input
                      className={inputBase}
                      required
                      value={adminManagerForm.username}
                      onChange={(event)=> setAdminManagerForm({ ...adminManagerForm, username: event.target.value })}
                    />
                  </label>

                  <label className={labelBase}>
                    First Name
                    <input
                      className={inputBase}
                      value={adminManagerForm.first_name}
                      onChange={(event)=> setAdminManagerForm({ ...adminManagerForm, first_name: event.target.value })}
                    />
                  </label>

                  <label className={labelBase}>
                    Last Name
                    <input
                      className={inputBase}
                      value={adminManagerForm.last_name}
                      onChange={(event)=> setAdminManagerForm({ ...adminManagerForm, last_name: event.target.value })}
                    />
                  </label>

                  <label className={`${labelBase} md:col-span-2`}>
                    Email
                    <input
                      className={inputBase}
                      type="email"
                      required
                      value={adminManagerForm.email}
                      onChange={(event)=> setAdminManagerForm({ ...adminManagerForm, email: event.target.value })}
                    />
                  </label>

                  <label className={labelBase}>
                    Password
                    <div className="flex items-center gap-2">
                      <input
                        className={inputBase}
                        type={showAdminPassword ? 'text' : 'password'}
                        required
                        minLength={8}
                        value={adminManagerForm.password}
                        onChange={(event)=> setAdminManagerForm({ ...adminManagerForm, password: event.target.value })}
                      />
                      <button
                        type="button"
                        className={iconBtn}
                        aria-label={showAdminPassword ? 'Hide password' : 'Show password'}
                        onMouseDown={(e)=> e.preventDefault()}
                        onClick={()=> setShowAdminPassword(s => !s)}
                      >
                        <i className={`fa ${showAdminPassword ? 'fa-eye-slash' : 'fa-eye'}`}></i>
                      </button>
                    </div>
                  </label>

                  <label className={labelBase}>
                    Role
                    <select
                      className={inputBase}
                      value={adminManagerForm.role}
                      onChange={(event)=> setAdminManagerForm({ ...adminManagerForm, role: event.target.value })}
                    >
                      <option value="manager">manager</option>
                      <option value="admin">admin</option>
                    </select>
                  </label>
                </>
              ) : (
                <>
                  <p className="md:col-span-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Register Employee User (No Token Required Endpoint)
                  </p>

                  <label className={labelBase}>
                    Username
                    <input
                      className={inputBase}
                      required
                      value={registerForm.username}
                      onChange={(event)=> setRegisterForm({ ...registerForm, username: event.target.value })}
                    />
                  </label>

                  <label className={labelBase}>
                    First Name
                    <input
                      className={inputBase}
                      required
                      value={registerForm.first_name}
                      onChange={(event)=> setRegisterForm({ ...registerForm, first_name: event.target.value })}
                    />
                  </label>

                  <label className={labelBase}>
                    Last Name
                    <input
                      className={inputBase}
                      value={registerForm.last_name}
                      onChange={(event)=> setRegisterForm({ ...registerForm, last_name: event.target.value })}
                    />
                  </label>

                  <label className={labelBase}>
                    Email
                    <input
                      className={inputBase}
                      type="email"
                      required
                      value={registerForm.email}
                      onChange={(event)=> setRegisterForm({ ...registerForm, email: event.target.value })}
                    />
                  </label>

                  <label className={labelBase}>
                    Password
                    <div className="flex items-center gap-2">
                      <input
                        className={inputBase}
                        type={showRegisterPassword ? 'text' : 'password'}
                        required
                        minLength={8}
                        value={registerForm.password}
                        onChange={(event)=> setRegisterForm({ ...registerForm, password: event.target.value })}
                      />
                      <button
                        type="button"
                        className={iconBtn}
                        aria-label={showRegisterPassword ? 'Hide password' : 'Show password'}
                        onMouseDown={(e)=> e.preventDefault()}
                        onClick={()=> setShowRegisterPassword(s => !s)}
                      >
                        <i className={`fa ${showRegisterPassword ? 'fa-eye-slash' : 'fa-eye'}`}></i>
                      </button>
                    </div>
                  </label>

                  <label className={labelBase}>
                    Relative
                    <input
                      className={inputBase}
                      required
                      value={registerForm.relative}
                      onChange={(event)=> setRegisterForm({ ...registerForm, relative: event.target.value })}
                    />
                  </label>

                  <label className={labelBase}>
                    Relative Phone
                    <input
                      className={inputBase}
                      required
                      value={registerForm.r_phone}
                      onChange={(event)=> setRegisterForm({ ...registerForm, r_phone: formatPhone(event.target.value) })}
                    />
                  </label>

                  <label className={labelBase}>
                    Start Time
                    <input
                      className={inputBase}
                      type="time"
                      required
                      value={registerForm.start_time}
                      onChange={(event)=> setRegisterForm({ ...registerForm, start_time: event.target.value })}
                    />
                  </label>

                  <label className={labelBase}>
                    End Time
                    <input
                      className={inputBase}
                      type="time"
                      required
                      value={registerForm.end_time}
                      onChange={(event)=> setRegisterForm({ ...registerForm, end_time: event.target.value })}
                    />
                  </label>

                  <label className={`${labelBase} md:col-span-2`}>
                    Address
                    <input
                      className={inputBase}
                      required
                      value={registerForm.address}
                      onChange={(event)=> setRegisterForm({ ...registerForm, address: event.target.value })}
                    />
                  </label>

                  <label className={`${labelBase} md:col-span-2`}>
                    Relative Address
                    <input
                      className={inputBase}
                      required
                      value={registerForm.r_address}
                      onChange={(event)=> setRegisterForm({ ...registerForm, r_address: event.target.value })}
                    />
                  </label>
                </>
              )}

              <div className="mt-2 flex flex-wrap justify-end gap-2 md:col-span-2">
                <button type="button" className={secondaryBtn} onClick={closeCreateModal}>Cancel</button>
                <button type="submit" className={primaryBtn} disabled={createBusy}>
                  {createBusy ? 'Creating...' : 'Create User'}
                </button>
              </div>
            </form>
          </div>
        </PortalModal>

      <PortalModal
        open={showEditModal}
        onClose={closeEditModal}
        overlayClassName="fixed inset-0 z-[70] flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm"
        innerClassName="w-full flex items-center justify-center px-4 md:px-0"
      >
        <div className="max-h-[92vh] w-full max-w-5xl overflow-auto rounded-2xl border border-slate-200 bg-white p-5 shadow-2xl relative">
          {editBusy && (
            <div className="absolute inset-0 z-10 bg-white/70 p-6 flex flex-col gap-3">
              <div className="skeleton h-6 w-40 rounded"></div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="skeleton h-10 w-full rounded"></div>
                <div className="skeleton h-10 w-full rounded"></div>
                <div className="skeleton h-10 w-full rounded"></div>
                <div className="skeleton h-10 w-full rounded"></div>
              </div>
              <div className="skeleton h-10 w-32 rounded mt-2"></div>
            </div>
          )}
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-xl font-semibold text-slate-800">Edit User</h3>
              <button className={iconBtn} type="button" onClick={closeEditModal}>
                <i className="fa fa-times"></i>
              </button>
            </div>

            <div className="mb-5 flex flex-col items-center justify-center gap-2">
              <input
                ref={editFileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleEditFileChange}
              />

              <div
                className="group relative flex h-32 w-32 cursor-pointer items-center justify-center overflow-hidden rounded-full border-2 border-dashed border-teal-300 bg-teal-50 transition hover:border-teal-500"
                onClick={handleEditAvatarClick}
                onDrop={handleEditDrop}
                onDragOver={handleEditDragOver}
                onKeyDown={(e)=> {
                  if(e.key === 'Enter' || e.key === ' ') handleEditAvatarClick()
                }}
                role="button"
                tabIndex={0}
              >
                {editPreviewUrl ? (
                  <>
                    <img src={editPreviewUrl} alt="avatar preview" className="h-full w-full object-cover" />
                    <button
                      type="button"
                      className="absolute right-1 top-1 inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white/95 text-rose-600 shadow"
                      onClick={handleEditRemoveImage}
                      aria-label="Remove image"
                    >
                      <i className="fa fa-trash"></i>
                    </button>
                  </>
                ) : (
                  <i className="fa fa-cloud-upload-alt text-3xl text-teal-600"></i>
                )}
                <span className="sr-only">Click or drop an image</span>
              </div>
              <p className="text-xs text-slate-500">Click or drag an image</p>
            </div>

            <form className="grid grid-cols-1 gap-3 md:grid-cols-2" onSubmit={submitEditUser}>
              <label className={labelBase}>
                Username
                <input
                  className={inputBase}
                  required
                  value={editForm.username || ''}
                  onChange={(e)=> setEditForm(prev => ({ ...prev, username: e.target.value }))}
                />
              </label>

              <label className={labelBase}>
                Email
                <input
                  className={inputBase}
                  type="email"
                  required
                  value={editForm.email || ''}
                  onChange={(e)=> setEditForm(prev => ({ ...prev, email: e.target.value }))}
                />
              </label>

              <label className={labelBase}>
                Role
                <select
                  className={inputBase}
                  value={editForm.role || 'employee'}
                  onChange={(e)=> setEditForm(prev => ({ ...prev, role: e.target.value }))}
                >
                  <option value="manager">manager</option>
                  <option value="admin">admin</option>
                  <option value="employee">employee</option>
                </select>
              </label>

              <label className={labelBase}>
                First Name
                <input
                  className={inputBase}
                  value={editForm.first_name || ''}
                  onChange={(e)=> setEditForm(prev => ({ ...prev, first_name: e.target.value }))}
                />
              </label>

              <label className={labelBase}>
                Last Name
                <input
                  className={inputBase}
                  value={editForm.last_name || ''}
                  onChange={(e)=> setEditForm(prev => ({ ...prev, last_name: e.target.value }))}
                />
              </label>
              <div className="mt-2 flex flex-wrap justify-end gap-2 md:col-span-2">
                <button type="button" className={secondaryBtn} onClick={closeEditModal}>Cancel</button>
                <button type="submit" className={primaryBtn} disabled={editBusy}>
                  {editBusy ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </PortalModal>
    </div>
  )
}
