-- DropForeignKey
ALTER TABLE "adjustments" DROP CONSTRAINT "adjustments_created_by_fkey";

-- AddForeignKey
ALTER TABLE "adjustments" ADD CONSTRAINT "adjustments_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
