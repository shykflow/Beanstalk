import { PrismaClient } from '@prisma/client'
import { addHours, subHours, startOfDay } from 'date-fns'
import { zonedTimeToUtc } from 'date-fns-tz'

const prisma = new PrismaClient()

async function main() {
  console.log('🌱 Seeding time entries...')

  // Get all users
  const users = await prisma.user.findMany({
    where: { isActive: true },
  })

  if (users.length === 0) {
    console.log('❌ No users found. Please run seed.ts first.')
    return
  }

  const timezone = 'Asia/Karachi'
  const today = new Date()
  
  // Create time entries for today in Pakistan time (17:00 - 21:00)
  // This is within the check-in window (16:50 - 02:00)
  
  for (const user of users) {
    console.log(`Creating time entries for ${user.email}...`)
    
    // Create entries from 17:00 to 21:00 Pakistan time (4 hours)
    const startTime = zonedTimeToUtc(
      new Date(today.getFullYear(), today.getMonth(), today.getDate(), 17, 0, 0),
      timezone
    )
    
    // Create 4 hours of active time with some breaks
    const entries = [
      {
        userId: user.id,
        startedAt: startTime,
        endedAt: addHours(startTime, 2), // 17:00 - 19:00 (2 hours active)
        kind: 'ACTIVE' as const,
        source: 'AUTO' as const,
      },
      {
        userId: user.id,
        startedAt: addHours(startTime, 2),
        endedAt: addHours(startTime, 2.5), // 19:00 - 19:30 (30 min idle)
        kind: 'IDLE' as const,
        source: 'AUTO' as const,
      },
      {
        userId: user.id,
        startedAt: addHours(startTime, 2.5),
        endedAt: addHours(startTime, 4), // 19:30 - 21:00 (1.5 hours active)
        kind: 'ACTIVE' as const,
        source: 'AUTO' as const,
      },
    ]
    
    for (const entry of entries) {
      await prisma.timeEntry.create({
        data: entry,
      })
    }
    
    console.log(`✅ Created ${entries.length} time entries for ${user.fullName}`)
  }

  // Also create some activity samples for realism
  console.log('\n📊 Creating activity samples...')
  
  for (const user of users) {
    const startTime = zonedTimeToUtc(
      new Date(today.getFullYear(), today.getMonth(), today.getDate(), 17, 0, 0),
      timezone
    )
    
    // Create samples every 5 minutes for 4 hours
    for (let i = 0; i < 48; i++) {
      const capturedAt = addHours(startTime, i * (5 / 60))
      
      await prisma.activitySample.create({
        data: {
          userId: user.id,
          capturedAt,
          mouseDelta: Math.floor(Math.random() * 1000) + 100,
          keyCount: Math.floor(Math.random() * 50) + 5,
        },
      })
    }
    
    console.log(`✅ Created 48 activity samples for ${user.fullName}`)
  }

  console.log('\n🎉 Time entries seeded successfully!')
  console.log('\n📊 Summary:')
  console.log(`- Users: ${users.length}`)
  console.log(`- Time entries per user: 3 (2h active + 30m idle + 1.5h active)`)
  console.log(`- Activity samples per user: 48`)
  console.log(`- Time range: 17:00 - 21:00 ${timezone} (today)`)
}

main()
  .catch((e) => {
    console.error('❌ Error seeding time entries:', e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
