'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { formatMinutes, formatDateTime } from '@/lib/utils'
import { Calendar, Clock } from 'lucide-react'

export default function TimesheetsPage() {
  const [users, setUsers] = useState<any[]>([])
  const [selectedUser, setSelectedUser] = useState<string>('')
  const [timesheet, setTimesheet] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [dateRange, setDateRange] = useState({
    from: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    to: new Date().toISOString().split('T')[0],
  })

  useEffect(() => {
    loadUsers()
  }, [])

  useEffect(() => {
    if (selectedUser) {
      loadTimesheet()
    }
  }, [selectedUser, dateRange])

  const loadUsers = async () => {
    try {
      const data = await api.getUsers()
      setUsers(data)
      if (data.length > 0) {
        setSelectedUser(data[0].id)
      }
    } catch (error) {
      console.error('Failed to load users:', error)
    }
  }

  const loadTimesheet = async () => {
    if (!selectedUser) return
    setLoading(true)
    try {
      const data = await api.getUserTimesheet(selectedUser, dateRange.from, dateRange.to)
      setTimesheet(data)
    } catch (error) {
      console.error('Failed to load timesheet:', error)
    } finally {
      setLoading(false)
    }
  }

  const totalMinutes = timesheet?.entries?.reduce((sum: number, entry: any) => {
    const start = new Date(entry.startedAt)
    const end = new Date(entry.endedAt)
    return sum + Math.floor((end.getTime() - start.getTime()) / 60000)
  }, 0) || 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">Timesheets</h1>
        <p className="mt-1 text-sm text-gray-500">📅 View detailed time entries for users</p>
      </div>

      {/* Filters */}
      <div className="rounded-xl bg-white shadow-lg p-6">
        <div className="flex items-center gap-2 mb-4">
          <Calendar className="h-5 w-5 text-primary" />
          <h3 className="font-semibold text-gray-900">Filter Options</h3>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">User</label>
            <select
              value={selectedUser}
              onChange={(e) => setSelectedUser(e.target.value)}
              className="block w-full rounded-lg border-2 border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all relative z-10"
            >
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.fullName || user.email}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">From</label>
            <input
              type="date"
              value={dateRange.from}
              onChange={(e) => setDateRange({ ...dateRange, from: e.target.value })}
              className="block w-full rounded-lg border-2 border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">To</label>
            <input
              type="date"
              value={dateRange.to}
              onChange={(e) => setDateRange({ ...dateRange, to: e.target.value })}
              className="block w-full rounded-lg border-2 border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
            />
          </div>
        </div>
      </div>

      {/* Summary */}
      {timesheet && (
        <div className="grid gap-6 md:grid-cols-2">
          <div className="group rounded-xl bg-gradient-to-br from-blue-50 via-blue-100 to-blue-50 p-6 shadow-lg transition-all hover:shadow-xl hover:scale-105">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-blue-600">Total Time</p>
                <p className="mt-2 text-4xl font-bold text-blue-900">
                  {formatMinutes(totalMinutes)}
                </p>
                <p className="mt-1 text-xs text-blue-600">Tracked hours</p>
              </div>
              <div className="rounded-full bg-blue-500 p-4 shadow-lg group-hover:scale-110 transition-transform">
                <Clock className="h-7 w-7 text-white" />
              </div>
            </div>
          </div>
          <div className="group rounded-xl bg-gradient-to-br from-purple-50 via-purple-100 to-purple-50 p-6 shadow-lg transition-all hover:shadow-xl hover:scale-105">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-purple-600">Total Entries</p>
                <p className="mt-2 text-4xl font-bold text-purple-900">
                  {timesheet.entries?.length || 0}
                </p>
                <p className="mt-1 text-xs text-purple-600">Time records</p>
              </div>
              <div className="rounded-full bg-purple-500 p-4 shadow-lg group-hover:scale-110 transition-transform">
                <Calendar className="h-7 w-7 text-white" />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Entries */}
      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-gray-200 border-t-primary"></div>
        </div>
      ) : (
        <div className="rounded-xl bg-white shadow-lg">
          <div className="border-b border-gray-200 bg-gradient-to-r from-gray-50 to-gray-100 px-6 py-4">
            <h2 className="text-lg font-semibold text-gray-900">📊 Time Entries</h2>
            <p className="text-xs text-gray-500 mt-1">{timesheet?.entries?.length || 0} entries found</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Started At
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Ended At
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Duration
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Source
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {timesheet?.entries?.map((entry: any) => {
                  const start = new Date(entry.startedAt)
                  const end = new Date(entry.endedAt)
                  const minutes = Math.floor((end.getTime() - start.getTime()) / 60000)
                  return (
                    <tr key={entry.id} className="hover:bg-gray-50 transition-colors">
                      <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
                        {formatDateTime(entry.startedAt)}
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
                        {formatDateTime(entry.endedAt)}
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">
                        {formatMinutes(minutes)}
                      </td>
                      <td className="whitespace-nowrap px-6 py-4">
                        <span
                          className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${
                            entry.kind === 'ACTIVE'
                              ? 'bg-green-100 text-green-700'
                              : entry.kind === 'IDLE'
                              ? 'bg-yellow-100 text-yellow-700'
                              : 'bg-gray-100 text-gray-700'
                          }`}
                        >
                          {entry.kind}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-6 py-4">
                        <span className="inline-flex rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700">
                          {entry.source}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
