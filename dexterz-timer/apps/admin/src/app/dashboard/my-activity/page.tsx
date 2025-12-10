'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { formatMinutes } from '@/lib/utils'
import { Clock, Activity, Coffee } from 'lucide-react'

export default function MyActivityPage() {
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStats()
    const interval = setInterval(loadStats, 60000) // Refresh every minute
    return () => clearInterval(interval)
  }, [])

  const loadStats = async () => {
    setLoading(true)
    try {
      const data = await api.getMyTodayStats()
      setStats(data)
    } catch (error) {
      console.error('Failed to load stats:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-12 w-64 bg-gray-200 rounded-lg"></div>
        <div className="grid gap-6 md:grid-cols-2">
          <div className="h-32 bg-gray-200 rounded-xl"></div>
          <div className="h-32 bg-gray-200 rounded-xl"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
          My Activity
        </h1>
        <p className="mt-1 text-sm text-gray-500">📊 Your activity for today</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="group rounded-xl bg-gradient-to-br from-green-50 via-green-100 to-green-50 p-6 shadow-lg transition-all hover:shadow-xl hover:scale-105">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-green-600">Active Time</p>
              <p className="mt-2 text-4xl font-bold text-green-900">
                {formatMinutes(stats?.activeMinutes || 0)}
              </p>
              <p className="mt-1 text-xs text-green-600">Productive work time</p>
            </div>
            <div className="rounded-full bg-green-500 p-4 shadow-lg group-hover:scale-110 transition-transform">
              <Activity className="h-7 w-7 text-white" />
            </div>
          </div>
        </div>

        <div className="group rounded-xl bg-gradient-to-br from-yellow-50 via-yellow-100 to-yellow-50 p-6 shadow-lg transition-all hover:shadow-xl hover:scale-105">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-yellow-600">Idle Time</p>
              <p className="mt-2 text-4xl font-bold text-yellow-900">
                {formatMinutes(stats?.idleMinutes || 0)}
              </p>
              <p className="mt-1 text-xs text-yellow-600">Inactive periods</p>
            </div>
            <div className="rounded-full bg-yellow-500 p-4 shadow-lg group-hover:scale-110 transition-transform">
              <Coffee className="h-7 w-7 text-white" />
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-xl bg-white shadow-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">💡 Tips</h2>
        <ul className="space-y-2 text-sm text-gray-600">
          <li>• Keep the desktop app running to track your activity</li>
          <li>• Active time is counted when you're using keyboard/mouse</li>
          <li>• Idle time starts after 5 minutes of inactivity</li>
          <li>• Break time (22:00-23:00) is not counted</li>
        </ul>
      </div>
    </div>
  )
}
