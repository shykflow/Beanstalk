import { PrismaClient } from '@prisma/client'
import { addMinutes } from 'date-fns'
import { zonedTimeToUtc } from 'date-fns-tz'

const prisma = new PrismaClient()

async function main() {
  console.log('🌱 Cleaning and seeding time tracker data...')

  // Get all users
  const users = await prisma.user.findMany({
    where: { 
      isActive: true,
      email: {
        in: ['admin@timetracker.com', 'manager@timetracker.com', 'member@timetracker.com']
      }
    },
  })

  if (users.length === 0) {
    console.log('❌ No users found. Please run seed.ts first.')
    return
  }

  console.log(`Found ${users.length} users to seed data for`)

  // Clean up existing data for today
  console.log('\n🧹 Cleaning up existing time entries and activity samples...')
  
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  
  await prisma.activitySample.deleteMany({
    where: {
      capturedAt: {
        gte: today,
      },
    },
  })
  
  await prisma.timeEntry.deleteMany({
    where: {
      startedAt: {
        gte: today,
      },
    },
  })
  
  console.log('✅ Cleaned up existing data')

  const timezone = 'Asia/Karachi'
  
  // Create ONLY activity samples - let the rollup service create time entries
  console.log('\n📊 Creating activity samples...')
  console.log('Time range: 17:00 - 21:00 Asia/Karachi (today)')
  console.log('This will simulate 4 hours of work with realistic activity patterns\n')
  
  for (const user of users) {
    console.log(`Creating activity samples for ${user.fullName || user.email}...`)
    
    // Start at 17:00 Pakistan time
    const startTime = zonedTimeToUtc(
      new Date(today.getFullYear(), today.getMonth(), today.getDate(), 17, 0, 0),
      timezone
    )
    
    // Create samples every 10 seconds for 4 hours (1440 samples)
    // This simulates realistic desktop app behavior
    const totalMinutes = 240 // 4 hours
    const samplesPerMinute = 6 // Every 10 seconds
    const totalSamples = totalMinutes * samplesPerMinute
    
    const samples: Array<{
      userId: string
      capturedAt: Date
      mouseDelta: number
      keyCount: number
    }> = []
    
    for (let i = 0; i < totalSamples; i++) {
      const capturedAt = addMinutes(startTime, i / samplesPerMinute)
      
      // Simulate realistic activity patterns
      // - First 2 hours: high activity
      // - 19:00-19:30: low activity (break/idle)
      // - Last 1.5 hours: medium-high activity
      
      const minutesSinceStart = i / samplesPerMinute
      let mouseDelta = 0
      let keyCount = 0
      
      if (minutesSinceStart < 120) {
        // First 2 hours: active work
        mouseDelta = Math.floor(Math.random() * 800) + 200
        keyCount = Math.floor(Math.random() * 40) + 10
      } else if (minutesSinceStart < 150) {
        // 19:00-19:30: break/idle (30 minutes)
        mouseDelta = Math.floor(Math.random() * 50)
        keyCount = Math.floor(Math.random() * 5)
      } else {
        // Last 1.5 hours: active work
        mouseDelta = Math.floor(Math.random() * 700) + 150
        keyCount = Math.floor(Math.random() * 35) + 8
      }
      
      samples.push({
        userId: user.id,
        capturedAt,
        mouseDelta,
        keyCount,
      })
    }
    
    // Insert in batches of 500 for performance
    const batchSize = 500
    for (let i = 0; i < samples.length; i += batchSize) {
      const batch = samples.slice(i, i + batchSize)
      await prisma.activitySample.createMany({
        data: batch,
      })
    }
    
    console.log(`✅ Created ${samples.length} activity samples for ${user.fullName || user.email}`)
  }

  console.log('\n✨ Activity samples created successfully!')
  console.log('\n📝 Next steps:')
  console.log('1. The rollup processor will automatically process these samples')
  console.log('2. Time entries will be created based on activity patterns')
  console.log('3. Expected result: ~3.5 hours of active time per user (with 30min idle period)')
  console.log('\n💡 To trigger rollup manually, you can call the rollup API endpoint')
}

main()
  .catch((e) => {
    console.error('❌ Error seeding data:', e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
