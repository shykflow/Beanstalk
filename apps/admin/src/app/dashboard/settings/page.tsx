'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { toast } from '@/lib/toast'
import { Building2, Clock, Coffee, Timer, Globe, Save } from 'lucide-react'

export default function SettingsPage() {
  const [organization, setOrganization] = useState<any>(null)
  const [schedule, setSchedule] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [org, sched] = await Promise.all([
        api.getOrganization(),
        api.getSchedule(),
      ])
      setOrganization(org)
      setSchedule(sched)
    } catch (error) {
      console.error('Failed to load settings:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveOrg = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.updateOrganization({
        name: organization.name,
        timezone: organization.timezone,
      })
      toast.success('Organization settings saved successfully')
    } catch (error) {
      console.error('Failed to save organization:', error)
      toast.error('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveSchedule = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.updateSchedule({
        tz: schedule.tz,
        checkinStart: schedule.checkinStart,
        checkinEnd: schedule.checkinEnd,
        breakStart: schedule.breakStart,
        breakEnd: schedule.breakEnd,
        idleThresholdSeconds: parseInt(schedule.idleThresholdSeconds),
      })
      toast.success('Schedule settings saved successfully')
    } catch (error) {
      console.error('Failed to save schedule:', error)
      toast.error('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-20 bg-gray-200 rounded-lg"></div>
        <div className="h-64 bg-gray-200 rounded-xl"></div>
        <div className="h-96 bg-gray-200 rounded-xl"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">Settings</h1>
        <p className="mt-1 text-sm text-gray-500">⚙️ Manage organization and schedule settings</p>
      </div>

      {/* Organization Settings */}
      <div className="rounded-xl bg-white shadow-lg">
        <div className="border-b border-gray-200 bg-gradient-to-r from-blue-50 to-blue-100 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-blue-500 p-2">
              <Building2 className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Organization Settings</h2>
              <p className="text-xs text-gray-600">Configure your organization details</p>
            </div>
          </div>
        </div>
        <div className="p-6">
        <form onSubmit={handleSaveOrg} className="space-y-4">
          <div className="space-y-4">
            <div>
              <label className="flex items-center gap-2 text-sm font-semibold text-gray-700">
                <Building2 className="h-4 w-4 text-gray-500" />
                Organization Name
              </label>
              <input
                type="text"
                value={organization?.name || ''}
                onChange={(e) =>
                  setOrganization({ ...organization, name: e.target.value })
                }
                className="mt-2 block w-full rounded-lg border-2 border-gray-300 px-4 py-2.5 shadow-sm transition-all focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                placeholder="Enter organization name"
              />
            </div>
            <div>
              <label className="flex items-center gap-2 text-sm font-semibold text-gray-700">
                <Globe className="h-4 w-4 text-gray-500" />
                Timezone
              </label>
              <input
                type="text"
                value={organization?.timezone || ''}
                onChange={(e) =>
                  setOrganization({ ...organization, timezone: e.target.value })
                }
                className="mt-2 block w-full rounded-lg border-2 border-gray-300 px-4 py-2.5 shadow-sm transition-all focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                placeholder="e.g., Asia/Karachi"
              />
              <p className="mt-2 flex items-center gap-1 text-xs text-gray-500">
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-blue-500"></span>
                Use IANA timezone format (e.g., Asia/Karachi, America/New_York)
              </p>
            </div>
          </div>
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-primary to-primary/90 px-6 py-2.5 font-semibold text-white shadow-md transition-all hover:shadow-lg hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Save className="h-4 w-4" />
            {saving ? 'Saving...' : 'Save Organization'}
          </button>
        </form>
        </div>
      </div>

      {/* Schedule Settings */}
      <div className="rounded-xl bg-white shadow-lg">
        <div className="border-b border-gray-200 bg-gradient-to-r from-green-50 to-green-100 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-green-500 p-2">
              <Clock className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Work Schedule</h2>
              <p className="text-xs text-gray-600">Define working hours and break times</p>
            </div>
          </div>
        </div>
        <div className="p-6">
        <form onSubmit={handleSaveSchedule} className="space-y-6">
          <div>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-4">
              <Clock className="h-4 w-4 text-green-600" />
              Working Hours
            </h3>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Start Time
                </label>
                <input
                  type="time"
                  value={schedule?.checkinStart || ''}
                  onChange={(e) =>
                    setSchedule({ ...schedule, checkinStart: e.target.value })
                  }
                  className="block w-full rounded-lg border-2 border-gray-300 px-4 py-2.5 shadow-sm transition-all focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  End Time
                </label>
                <input
                  type="time"
                  value={schedule?.checkinEnd || ''}
                  onChange={(e) =>
                    setSchedule({ ...schedule, checkinEnd: e.target.value })
                  }
                  className="block w-full rounded-lg border-2 border-gray-300 px-4 py-2.5 shadow-sm transition-all focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
            </div>
          </div>

          <div>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-4">
              <Coffee className="h-4 w-4 text-yellow-600" />
              Break Time
            </h3>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Start Time
                </label>
                <input
                  type="time"
                  value={schedule?.breakStart || ''}
                  onChange={(e) =>
                    setSchedule({ ...schedule, breakStart: e.target.value })
                  }
                  className="block w-full rounded-lg border-2 border-gray-300 px-4 py-2.5 shadow-sm transition-all focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  End Time
                </label>
                <input
                  type="time"
                  value={schedule?.breakEnd || ''}
                  onChange={(e) =>
                    setSchedule({ ...schedule, breakEnd: e.target.value })
                  }
                  className="block w-full rounded-lg border-2 border-gray-300 px-4 py-2.5 shadow-sm transition-all focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
            </div>
          </div>
          <div>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-4">
              <Timer className="h-4 w-4 text-purple-600" />
              Idle Detection
            </h3>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Idle Threshold (seconds)
              </label>
              <input
                type="number"
                value={schedule?.idleThresholdSeconds || ''}
                onChange={(e) =>
                  setSchedule({ ...schedule, idleThresholdSeconds: e.target.value })
                }
                className="block w-full rounded-lg border-2 border-gray-300 px-4 py-2.5 shadow-sm transition-all focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                placeholder="300"
              />
              <p className="mt-2 flex items-center gap-1 text-xs text-gray-500">
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-purple-500"></span>
                Consecutive idle time (in seconds) before marking as idle. Default: 300 (5 minutes)
              </p>
            </div>
          </div>
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-green-500 to-green-600 px-6 py-2.5 font-semibold text-white shadow-md transition-all hover:shadow-lg hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Save className="h-4 w-4" />
            {saving ? 'Saving...' : 'Save Schedule'}
          </button>
        </form>
        </div>
      </div>
    </div>
  )
}
