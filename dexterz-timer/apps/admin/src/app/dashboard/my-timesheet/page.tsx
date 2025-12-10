'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { formatMinutes, formatDate } from '@/lib/utils'
import { Clock, Activity, TrendingUp, Calendar, BarChart3 } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

export default function MyTimesheetPage() {
  const [timesheet, setTimesheet] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [viewType, setViewType] = useState<'daily' | 'weekly' | 'monthly'>('weekly')
  const [dateRange, setDateRange] = useState({
    from: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    to: new Date().toISOString().split('T')[0],
  })
  const [user, setUser] = useState<any>(null)

  useEffect(() => {
    const init = async () => {
      const userData = await loadUser()
      if (userData) {
        const range = calculateDateRange(viewType)
        setDateRange(range)
        await loadTimesheetData(userData.id, range.from, range.to)
      }
    }
    init()
  }, [])

  useEffect(() => {
    if (user) {
      const range = calculateDateRange(viewType)
      setDateRange(range)
      loadTimesheetData(user.id, range.from, range.to)
    }
  }, [viewType])

  const calculateDateRange = (type: 'daily' | 'weekly' | 'monthly') => {
    const now = new Date()
    const getLocalDate = (date: Date) => {
      const year = date.getFullYear()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')
      return `${year}-${month}-${day}`
    }
    
    const today = getLocalDate(now)
    let from, to
    
    if (type === 'daily') {
      from = to = today
    } else if (type === 'weekly') {
      const dayOfWeek = now.getDay()
      const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1
      const monday = new Date(now.getTime() - daysToMonday * 24 * 60 * 60 * 1000)
      from = getLocalDate(monday)
      to = today
    } else {
      const firstDay = new Date(now.getFullYear(), now.getMonth(), 1)
      from = getLocalDate(firstDay)
      to = today
    }
    
    return { from, to }
  }

  const loadUser = async () => {
    try {
      const userData = await api.getCurrentUser()
      setUser(userData)
      return userData
    } catch (error) {
      console.error('Failed to load user:', error)
      return null
    }
  }

  const loadTimesheetData = async (userId: string, from: string, to: string) => {
    setLoading(true)
    try {
      const data = await api.getUserTimesheet(userId, from, to)
      setTimesheet(data)
    } catch (error) {
      console.error('Failed to load timesheet:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading || !user) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
          My Timesheet
        </h1>
        <p className="mt-1 text-sm text-gray-500">📊 Detailed activity breakdown</p>
      </div>

      {/* View Type Tabs */}
      <div className="flex gap-2 bg-white rounded-lg p-2 shadow-md w-fit">
        <button
          onClick={() => setViewType('daily')}
          className={`px-6 py-2 rounded-lg font-semibold transition-all ${
            viewType === 'daily'
              ? 'bg-primary text-white shadow-md'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          📅 Daily
        </button>
        <button
          onClick={() => setViewType('weekly')}
          className={`px-6 py-2 rounded-lg font-semibold transition-all ${
            viewType === 'weekly'
              ? 'bg-primary text-white shadow-md'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          📆 Weekly
        </button>
        <button
          onClick={() => setViewType('monthly')}
          className={`px-6 py-2 rounded-lg font-semibold transition-all ${
            viewType === 'monthly'
              ? 'bg-primary text-white shadow-md'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          🗓️ Monthly
        </button>
      </div>

      {/* Date Range */}
      <div className="rounded-lg bg-white shadow-md p-4">
        <div className="flex items-center gap-4">
          <Calendar className="h-5 w-5 text-gray-400" />
          {viewType === 'daily' ? (
            <div>
              <label className="block text-xs font-medium text-gray-700">Select Date</label>
              <input
                type="date"
                value={dateRange.from}
                onChange={(e) => {
                  const newRange = { from: e.target.value, to: e.target.value }
                  setDateRange(newRange)
                  if (user) loadTimesheetData(user.id, newRange.from, newRange.to)
                }}
                className="mt-1 block rounded-md border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-primary"
              />
            </div>
          ) : (
            <div className="flex items-center gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-700">From</label>
                <input
                  type="date"
                  value={dateRange.from}
                  onChange={(e) => {
                    const newRange = { ...dateRange, from: e.target.value }
                    setDateRange(newRange)
                    if (user) loadTimesheetData(user.id, newRange.from, newRange.to)
                  }}
                  className="mt-1 block rounded-md border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-primary"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700">To</label>
                <input
                  type="date"
                  value={dateRange.to}
                  onChange={(e) => {
                    const newRange = { ...dateRange, to: e.target.value }
                    setDateRange(newRange)
                    if (user) loadTimesheetData(user.id, newRange.from, newRange.to)
                  }}
                  className="mt-1 block rounded-md border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-primary"
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-lg bg-gradient-to-br from-blue-50 to-blue-100 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-blue-600">Total Time</p>
              <p className="mt-1 text-xl font-bold text-blue-900">
                {formatMinutes(
                  timesheet?.entries?.reduce((sum: number, entry: any) => {
                    const start = new Date(entry.startedAt)
                    const end = new Date(entry.endedAt)
                    return sum + Math.floor((end.getTime() - start.getTime()) / 60000)
                  }, 0) || 0
                )}
              </p>
            </div>
            <Clock className="h-8 w-8 text-blue-600 opacity-50" />
          </div>
        </div>

        <div className="rounded-lg bg-gradient-to-br from-green-50 to-green-100 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-green-600">Active Time</p>
              <p className="mt-1 text-xl font-bold text-green-900">
                {formatMinutes(
                  timesheet?.entries
                    ?.filter((e: any) => e.kind === 'ACTIVE')
                    .reduce((sum: number, entry: any) => {
                      const start = new Date(entry.startedAt)
                      const end = new Date(entry.endedAt)
                      return sum + Math.floor((end.getTime() - start.getTime()) / 60000)
                    }, 0) || 0
                )}
              </p>
            </div>
            <Activity className="h-8 w-8 text-green-600 opacity-50" />
          </div>
        </div>

        <div className="rounded-lg bg-gradient-to-br from-yellow-50 to-yellow-100 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-yellow-600">Idle Time</p>
              <p className="mt-1 text-xl font-bold text-yellow-900">
                {formatMinutes(
                  timesheet?.entries
                    ?.filter((e: any) => e.kind === 'IDLE')
                    .reduce((sum: number, entry: any) => {
                      const start = new Date(entry.startedAt)
                      const end = new Date(entry.endedAt)
                      return sum + Math.floor((end.getTime() - start.getTime()) / 60000)
                    }, 0) || 0
                )}
              </p>
            </div>
            <Clock className="h-8 w-8 text-yellow-600 opacity-50" />
          </div>
        </div>

        <div className="rounded-lg bg-gradient-to-br from-purple-50 to-purple-100 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-purple-600">Activity Rate</p>
              <p className="mt-1 text-xl font-bold text-purple-900">
                {(() => {
                  const total = timesheet?.entries?.reduce((sum: number, entry: any) => {
                    const start = new Date(entry.startedAt)
                    const end = new Date(entry.endedAt)
                    return sum + Math.floor((end.getTime() - start.getTime()) / 60000)
                  }, 0) || 0
                  const active = timesheet?.entries
                    ?.filter((e: any) => e.kind === 'ACTIVE')
                    .reduce((sum: number, entry: any) => {
                      const start = new Date(entry.startedAt)
                      const end = new Date(entry.endedAt)
                      return sum + Math.floor((end.getTime() - start.getTime()) / 60000)
                    }, 0) || 0
                  return total > 0 ? Math.round((active / total) * 100) : 0
                })()}%
              </p>
            </div>
            <TrendingUp className="h-8 w-8 text-purple-600 opacity-50" />
          </div>
        </div>
      </div>

      {/* Activity Chart */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-200 bg-gradient-to-r from-gray-50 to-gray-100 px-6 py-4">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-primary" />
            <h3 className="font-semibold text-gray-900">Activity Overview</h3>
          </div>
        </div>
        <div className="p-6">
          <div className="grid gap-8 md:grid-cols-2">
            {/* Bar Chart */}
            <div className="rounded-lg bg-gradient-to-br from-gray-50 to-white p-4">
              <h4 className="mb-4 text-sm font-semibold text-gray-700">Daily Activity Breakdown</h4>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart
                  data={(() => {
                    const dailyData: any = {}
                    timesheet?.entries?.forEach((entry: any) => {
                      const date = formatDate(entry.startedAt)
                      if (!dailyData[date]) {
                        dailyData[date] = { date, active: 0, idle: 0 }
                      }
                      const start = new Date(entry.startedAt)
                      const end = new Date(entry.endedAt)
                      const minutes = Math.floor((end.getTime() - start.getTime()) / 60000)
                      if (entry.kind === 'ACTIVE') {
                        dailyData[date].active += minutes
                      } else {
                        dailyData[date].idle += minutes
                      }
                    })
                    return Object.values(dailyData)
                  })()}
                  margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="active" fill="#10b981" name="Active" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="idle" fill="#f59e0b" name="Idle" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Pie Chart */}
            <div className="rounded-lg bg-gradient-to-br from-gray-50 to-white p-4">
              <h4 className="mb-4 text-sm font-semibold text-gray-700">Time Distribution</h4>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={[
                      {
                        name: 'Active',
                        value: timesheet?.entries
                          ?.filter((e: any) => e.kind === 'ACTIVE')
                          .reduce((sum: number, entry: any) => {
                            const start = new Date(entry.startedAt)
                            const end = new Date(entry.endedAt)
                            return sum + Math.floor((end.getTime() - start.getTime()) / 60000)
                          }, 0) || 0,
                      },
                      {
                        name: 'Idle',
                        value: timesheet?.entries
                          ?.filter((e: any) => e.kind === 'IDLE')
                          .reduce((sum: number, entry: any) => {
                            const start = new Date(entry.startedAt)
                            const end = new Date(entry.endedAt)
                            return sum + Math.floor((end.getTime() - start.getTime()) / 60000)
                          }, 0) || 0,
                      },
                    ]}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent, value }) => 
                      value > 0 ? `${name}: ${(percent * 100).toFixed(1)}%` : ''
                    }
                    outerRadius={90}
                    innerRadius={50}
                    dataKey="value"
                  >
                    <Cell fill="#10b981" />
                    <Cell fill="#f59e0b" />
                  </Pie>
                  <Tooltip formatter={(value: number) => `${value} min`} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-200 bg-gray-50 px-4 py-3">
          <h3 className="font-semibold text-gray-900">Activity Timeline</h3>
          <p className="text-xs text-gray-500">
            {timesheet?.entries?.length || 0} entries
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Date</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Start</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">End</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Duration</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {timesheet?.entries?.map((entry: any) => {
                const start = new Date(entry.startedAt)
                const end = new Date(entry.endedAt)
                const minutes = Math.floor((end.getTime() - start.getTime()) / 60000)
                return (
                  <tr key={entry.id} className="hover:bg-gray-50">
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-900">
                      {formatDate(entry.startedAt)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                      {start.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                      {end.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                      {formatMinutes(minutes)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
                          entry.kind === 'ACTIVE'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {entry.kind}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {(!timesheet?.entries || timesheet.entries.length === 0) && (
            <div className="py-12 text-center text-sm text-gray-500">
              No activity recorded for this period
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
