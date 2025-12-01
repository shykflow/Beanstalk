'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

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
      alert('Organization settings saved successfully')
    } catch (error) {
      console.error('Failed to save organization:', error)
      alert('Failed to save settings')
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
      alert('Schedule settings saved successfully')
    } catch (error) {
      console.error('Failed to save schedule:', error)
      alert('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div>Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="mt-1 text-sm text-gray-500">Manage organization and schedule settings</p>
      </div>

      {/* Organization Settings */}
      <div className="rounded-lg bg-white p-6 shadow">
        <h2 className="text-lg font-semibold text-gray-900">Organization</h2>
        <form onSubmit={handleSaveOrg} className="mt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Organization Name
            </label>
            <input
              type="text"
              value={organization?.name || ''}
              onChange={(e) =>
                setOrganization({ ...organization, name: e.target.value })
              }
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary focus:outline-none focus:ring-primary"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Timezone</label>
            <input
              type="text"
              value={organization?.timezone || ''}
              onChange={(e) =>
                setOrganization({ ...organization, timezone: e.target.value })
              }
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary focus:outline-none focus:ring-primary"
            />
            <p className="mt-1 text-xs text-gray-500">e.g., Asia/Karachi</p>
          </div>
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-primary px-4 py-2 text-white hover:bg-primary/90 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Organization'}
          </button>
        </form>
      </div>

      {/* Schedule Settings */}
      <div className="rounded-lg bg-white p-6 shadow">
        <h2 className="text-lg font-semibold text-gray-900">Work Schedule</h2>
        <form onSubmit={handleSaveSchedule} className="mt-4 space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Check-in Start Time
              </label>
              <input
                type="time"
                value={schedule?.checkinStart || ''}
                onChange={(e) =>
                  setSchedule({ ...schedule, checkinStart: e.target.value })
                }
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary focus:outline-none focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Check-in End Time
              </label>
              <input
                type="time"
                value={schedule?.checkinEnd || ''}
                onChange={(e) =>
                  setSchedule({ ...schedule, checkinEnd: e.target.value })
                }
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary focus:outline-none focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Break Start Time
              </label>
              <input
                type="time"
                value={schedule?.breakStart || ''}
                onChange={(e) =>
                  setSchedule({ ...schedule, breakStart: e.target.value })
                }
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary focus:outline-none focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Break End Time
              </label>
              <input
                type="time"
                value={schedule?.breakEnd || ''}
                onChange={(e) =>
                  setSchedule({ ...schedule, breakEnd: e.target.value })
                }
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary focus:outline-none focus:ring-primary"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Idle Threshold (seconds)
            </label>
            <input
              type="number"
              value={schedule?.idleThresholdSeconds || ''}
              onChange={(e) =>
                setSchedule({ ...schedule, idleThresholdSeconds: e.target.value })
              }
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary focus:outline-none focus:ring-primary"
            />
            <p className="mt-1 text-xs text-gray-500">
              Time in seconds before considering user idle (default: 300)
            </p>
          </div>
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-primary px-4 py-2 text-white hover:bg-primary/90 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Schedule'}
          </button>
        </form>
      </div>
    </div>
  )
}
