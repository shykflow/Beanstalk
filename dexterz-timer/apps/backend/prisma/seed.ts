import { PrismaClient } from '@prisma/client'
import * as bcrypt from 'bcrypt'

const prisma = new PrismaClient()

async function main() {
  console.log('🌱 Starting database seed...')

  // Create organization
  const org = await prisma.organization.upsert({
    where: { id: '00000000-0000-0000-0000-000000000001' },
    update: {
      name: 'Dexterz Technologies',
    },
    create: {
      id: '00000000-0000-0000-0000-000000000001',
      name: 'Dexterz Technologies',
      timezone: 'Asia/Karachi',
    },
  })
  console.log('✅ Organization created:', org.name)

  // Create default schedule for organization
  const schedule = await prisma.schedule.upsert({
    where: { orgId: org.id },
    update: {},
    create: {
      orgId: org.id,
      tz: 'Asia/Karachi',
      checkinStart: '16:50',
      checkinEnd: '02:00',
      breakStart: '22:00',
      breakEnd: '23:00',
      idleThresholdSeconds: 300,
    },
  })
  console.log('✅ Schedule created for organization')

  // Create admin user
  const passwordHash = await bcrypt.hash('admin123', 10)
  
  const adminUser = await prisma.user.upsert({
    where: { email: 'admin@timetracker.com' },
    update: {},
    create: {
      email: 'admin@timetracker.com',
      passwordHash,
      fullName: 'Admin User',
      role: 'OWNER',
      orgId: org.id,
      isActive: true,
    },
  })
  console.log('✅ Admin user created')
  console.log('   Email: admin@timetracker.com')
  console.log('   Password: admin123')
  console.log('   Role: OWNER')

  // Create a few sample users
  const users = [
    {
      email: 'manager@timetracker.com',
      password: 'manager123',
      fullName: 'Manager User',
      role: 'MANAGER' as const,
    },
    {
      email: 'member@timetracker.com',
      password: 'member123',
      fullName: 'Member User',
      role: 'MEMBER' as const,
    },
  ]

  for (const userData of users) {
    const hash = await bcrypt.hash(userData.password, 10)
    const user = await prisma.user.upsert({
      where: { email: userData.email },
      update: {},
      create: {
        email: userData.email,
        passwordHash: hash,
        fullName: userData.fullName,
        role: userData.role,
        orgId: org.id,
        isActive: true,
      },
    })
    console.log(`✅ ${userData.role} user created: ${userData.email}`)
  }

  console.log('\n🎉 Database seeded successfully!')
  console.log('\n📝 Login Credentials:')
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log('Admin (OWNER):')
  console.log('  Email: admin@timetracker.com')
  console.log('  Password: admin123')
  console.log('\nManager:')
  console.log('  Email: manager@timetracker.com')
  console.log('  Password: manager123')
  console.log('\nMember:')
  console.log('  Email: member@timetracker.com')
  console.log('  Password: member123')
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')
}

main()
  .catch((e) => {
    console.error('❌ Error seeding database:', e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
