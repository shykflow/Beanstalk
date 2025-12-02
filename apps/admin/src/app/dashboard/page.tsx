'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { formatMinutes, formatDate } from '@/lib/utils'
import { Users, Clock, TrendingUp } from 'lucide-react'

export default function DashboardPage() {
  const [report, setReport] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0])

  useEffect(() => {
    loadReport()
  }, [selectedDate])

  const loadReport = async () => {
    setLoading(true)
    try {
      const data = await api.getDailyReport(selectedDate)
      setReport(data)
    } catch (error) {
      console.error('Failed to load report:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="flex items-center justify-between">
          <div className="h-12 w-64 bg-gray-200 rounded-lg"></div>
          <div className="h-10 w-40 bg-gray-200 rounded-lg"></div>
        </div>
        <div className="grid gap-6 md:grid-cols-3">
          <div className="h-32 bg-gray-200 rounded-xl"></div>
          <div className="h-32 bg-gray-200 rounded-xl"></div>
          <div className="h-32 bg-gray-200 rounded-xl"></div>
        </div>
        <div className="h-96 bg-gray-200 rounded-xl"></div>
      </div>
    )
  }

  const totalMinutes = report?.users?.reduce(
    (sum: number, user: any) => sum + user.totalMinutes,
    0
  ) || 0

  const totalActiveMinutes = report?.users?.reduce(
    (sum: number, user: any) => sum + user.activeMinutes,
    0
  ) || 0

  const activeUsers = report?.users?.filter((u: any) => u.totalMinutes > 0).length || 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">
            📊 Overview for {report?.date ? formatDate(report.date) : 'today'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">Select Date:</label>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="rounded-lg border-2 border-gray-300 px-4 py-2 text-sm font-medium shadow-sm transition-all focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-6 md:grid-cols-3">
        <div className="group rounded-xl bg-gradient-to-br from-blue-50 via-blue-100 to-blue-50 p-6 shadow-lg transition-all hover:shadow-xl hover:scale-105">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-blue-600">Active Users</p>
              <p className="mt-2 text-4xl font-bold text-blue-900">{activeUsers}</p>
              <p className="mt-1 text-xs text-blue-600">Currently tracking</p>
            </div>
            <div className="rounded-full bg-blue-500 p-4 shadow-lg group-hover:scale-110 transition-transform">
              <Users className="h-7 w-7 text-white" />
            </div>
          </div>
        </div>

        <div className="group rounded-xl bg-gradient-to-br from-green-50 via-green-100 to-green-50 p-6 shadow-lg transition-all hover:shadow-xl hover:scale-105">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-green-600">Total Hours</p>
              <p className="mt-2 text-4xl font-bold text-green-900">
                {formatMinutes(totalMinutes)}
              </p>
              <p className="mt-1 text-xs text-green-600">Total tracked time</p>
            </div>
            <div className="rounded-full bg-green-500 p-4 shadow-lg group-hover:scale-110 transition-transform">
              <Clock className="h-7 w-7 text-white" />
            </div>
          </div>
        </div>

        <div className="group rounded-xl bg-gradient-to-br from-purple-50 via-purple-100 to-purple-50 p-6 shadow-lg transition-all hover:shadow-xl hover:scale-105">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-purple-600">Avg per User</p>
              <p className="mt-2 text-4xl font-bold text-purple-900">
                {activeUsers > 0
                  ? formatMinutes(Math.round(totalMinutes / activeUsers))
                  : '0h 0m'}
              </p>
              <p className="mt-1 text-xs text-purple-600">Average total time</p>
            </div>
            <div className="rounded-full bg-purple-500 p-4 shadow-lg group-hover:scale-110 transition-transform">
              <TrendingUp className="h-7 w-7 text-white" />
            </div>
          </div>
        </div>
      </div>

      {/* User List */}
      <div className="rounded-xl bg-white shadow-lg">
        <div className="border-b border-gray-200 bg-gradient-to-r from-gray-50 to-gray-100 px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">📈 Activity Breakdown</h2>
          <p className="text-xs text-gray-500 mt-1">Detailed user activity for selected date</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  User
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Active Time
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Idle Time
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Total Time
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {report?.users?.length > 0 ? (
                report.users.map((user: any) => (
                  <tr key={user.userId} className="hover:bg-gray-50 transition-colors">
                    <td className="whitespace-nowrap px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-full bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center text-white font-semibold shadow-md">
                          {user.userName?.charAt(0).toUpperCase() || 'U'}
                        </div>
                        <div className="text-sm font-medium text-gray-900">{user.userName}</div>
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4">
                      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-3 py-1 text-sm font-semibold text-green-700">
                        {formatMinutes(user.activeMinutes)}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4">
                      <span className="inline-flex items-center gap-1 rounded-full bg-yellow-100 px-3 py-1 text-sm font-semibold text-yellow-700">
                        {formatMinutes(user.idleMinutes)}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4">
                      <span className="text-sm font-bold text-gray-900">
                        {formatMinutes(user.totalMinutes)}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="px-6 py-12 text-center">
                    <div className="flex flex-col items-center gap-2">
                      <Clock className="h-12 w-12 text-gray-300" />
                      <p className="text-sm font-medium text-gray-500">No activity recorded</p>
                      <p className="text-xs text-gray-400">Users will appear here once they start tracking</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
