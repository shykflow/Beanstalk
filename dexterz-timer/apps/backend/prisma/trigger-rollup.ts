import { PrismaClient } from '@prisma/client'
import { RollupService } from '../src/activity/rollup.service'
import { startOfDay, endOfDay } from 'date-fns'

const prisma = new PrismaClient()

async function main() {
  console.log('🔄 Triggering rollup for all users...\n')

  const rollupService = new RollupService(prisma as any)

  // Get all active users
  const users = await prisma.user.findMany({
    where: { 
      isActive: true,
      email: {
        in: ['admin@timetracker.com', 'manager@timetracker.com', 'member@timetracker.com']
      }
    },
  })

  if (users.length === 0) {
    console.log('❌ No users found')
    return
  }

  const today = new Date()
  const from = startOfDay(today)
  const to = endOfDay(today)

  console.log(`Processing activity from ${from.toISOString()} to ${to.toISOString()}\n`)

  for (const user of users) {
    console.log(`Processing ${user.fullName || user.email}...`)
    
    try {
      const result = await rollupService.rollupUserActivity(user.id, from, to)
      console.log(`✅ Processed ${result?.processed || 0} time entries for ${user.fullName || user.email}`)
    } catch (error) {
      console.error(`❌ Error processing ${user.fullName || user.email}:`, error)
    }
  }

  // Verify results
  console.log('\n📊 Verification:')
  const timeEntries = await prisma.timeEntry.findMany({
    where: {
      userId: { in: users.map(u => u.id) },
      startedAt: { gte: from },
    },
    include: {
      user: {
        select: {
          fullName: true,
          email: true,
        },
      },
    },
  })

  const userStats = new Map<string, { count: number; totalMinutes: number }>()

  for (const entry of timeEntries) {
    const userName = entry.user.fullName || entry.user.email
    const minutes = (entry.endedAt.getTime() - entry.startedAt.getTime()) / (1000 * 60)
    
    if (!userStats.has(userName)) {
      userStats.set(userName, { count: 0, totalMinutes: 0 })
    }
    
    const stats = userStats.get(userName)!
    stats.count++
    stats.totalMinutes += minutes
  }

  console.log('\nResults:')
  for (const [userName, stats] of userStats.entries()) {
    const hours = Math.floor(stats.totalMinutes / 60)
    const minutes = Math.round(stats.totalMinutes % 60)
    console.log(`  ${userName}: ${stats.count} entries, ${hours}h ${minutes}m total`)
  }

  console.log('\n✨ Rollup complete!')
}

main()
  .catch((e) => {
    console.error('❌ Error:', e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
