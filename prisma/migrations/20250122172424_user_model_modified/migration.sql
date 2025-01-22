/*
  Warnings:

  - You are about to drop the column `jobId` on the `Tracked_Jobs` table. All the data in the column will be lost.
  - You are about to drop the `User_Jobs` table. If the table is not empty, all the data it contains will be lost.
  - A unique constraint covering the columns `[title,companyId,userId]` on the table `Tracked_Jobs` will be added. If there are existing duplicate values, this will fail.
  - Added the required column `title` to the `Tracked_Jobs` table without a default value. This is not possible if the table is not empty.

*/
-- DropForeignKey
ALTER TABLE "Tracked_Jobs" DROP CONSTRAINT "Tracked_Jobs_jobId_fkey";

-- DropForeignKey
ALTER TABLE "User_Jobs" DROP CONSTRAINT "User_Jobs_companyId_fkey";

-- DropForeignKey
ALTER TABLE "User_Jobs" DROP CONSTRAINT "User_Jobs_userId_fkey";

-- DropIndex
DROP INDEX "Tracked_Jobs_jobId_userId_key";

-- AlterTable
ALTER TABLE "Tracked_Jobs" DROP COLUMN "jobId",
ADD COLUMN     "apply_link" TEXT,
ADD COLUMN     "companyId" UUID,
ADD COLUMN     "job_description" TEXT,
ADD COLUMN     "job_link" TEXT,
ADD COLUMN     "job_location" TEXT,
ADD COLUMN     "job_salary" TEXT,
ADD COLUMN     "job_type" TEXT,
ADD COLUMN     "posted" TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN     "skills_required" TEXT,
ADD COLUMN     "source" TEXT,
ADD COLUMN     "source_logo" TEXT,
-- Make 'title' nullable temporarily or add a default value:
ADD COLUMN     "title" TEXT DEFAULT 'Default Title';

-- DropTable
-- Backup the table data if needed:
-- CREATE TABLE "User_Jobs_backup" AS SELECT * FROM "User_Jobs";
DROP TABLE "User_Jobs";

-- CreateIndex
-- Ensure no duplicate values exist before applying:
CREATE UNIQUE INDEX "Tracked_Jobs_title_companyId_userId_key" ON "Tracked_Jobs"("title", "companyId", "userId");

-- AddForeignKey
ALTER TABLE "Tracked_Jobs" ADD CONSTRAINT "Tracked_Jobs_companyId_fkey" FOREIGN KEY ("companyId") REFERENCES "Company"("id") ON DELETE SET NULL ON UPDATE CASCADE;
