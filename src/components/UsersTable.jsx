import React from 'react'

export default function UsersTable(props){
  const {
    users = [],
    loading = false,
    editingRoles = {},
    savingRoles = {},
    rowErrors = {},
    beginEditRole,
    cancelEditRole,
    changeRoleLocal,
    saveRole,
    removeAccessLevel,
    lastRoleChange,
    undoRole,
    getInitials
    ,
    openEditUser
  } = props

  function roleBadgeClass(role){
    if(role === 'admin') return 'bg-sky-100 text-sky-700'
    if(role === 'manager') return 'bg-emerald-100 text-emerald-700'
    return 'bg-slate-100 text-slate-700'
  }

  return (
    <div className="users-table table-scroll overflow-x-auto rounded-xl border border-slate-200">
      <table className="min-w-[860px] w-full text-sm">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">User</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">Role</th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-600 w-36">Actions</th>
          </tr>
        </thead>
        <tbody>
          {loading && (
            <tr>
              <td colSpan="3" className="px-4 py-6 text-center text-slate-500">Loading users...</td>
            </tr>
          )}

          {!loading && users.length === 0 && (
            <tr>
              <td colSpan="3" className="px-4 py-6 text-center text-slate-500">No users found.</td>
            </tr>
          )}

          {!loading && users.map((u) => (
            <tr key={u.id || u.user || u.username} className="border-t border-slate-200 hover:bg-teal-50/30">
              <td className="px-4 py-3">
                <div className="flex items-center gap-3">
                  {u.profile_img ? (
                    <img className="h-12 w-12 rounded-full object-cover" src={u.profile_img} alt={u.username || 'avatar'} />
                  ) : (
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-200 text-sm font-bold text-slate-700">{getInitials(u)}</div>
                  )}
                  <div className="min-w-0">
                    <div className="truncate font-semibold text-slate-800">{u.username || u.user || '-'}</div>
                    <div className="truncate text-xs text-slate-500">{u.email || '-'}</div>
                  </div>
                </div>
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${roleBadgeClass(u.role || 'employee')}`}>
                    {u.role || '-'}
                  </span>
                  {lastRoleChange && lastRoleChange.id === u.id ? (
                    <button
                      className="rounded-lg border border-amber-300 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700 transition hover:bg-amber-100"
                      type="button"
                      onClick={() => undoRole(u.id)}
                    >
                      Undo
                    </button>
                  ) : null}
                </div>
                {rowErrors[u.id] ? <div className="mt-1 text-xs text-rose-600">{rowErrors[u.id]}</div> : null}
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center justify-end gap-2">
                  <button
                    className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-700 transition hover:bg-slate-100"
                    type="button"
                    title="Edit user"
                    onClick={() => openEditUser ? openEditUser(u) : null}
                  >
                    <i className="fa fa-pen"></i>
                  </button>
                  <button
                    className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-rose-300 bg-white text-rose-600 transition hover:bg-rose-50"
                    type="button"
                    title="Remove access level"
                    onClick={() => removeAccessLevel(u)}
                  >
                    <i className="fa fa-trash"></i>
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
