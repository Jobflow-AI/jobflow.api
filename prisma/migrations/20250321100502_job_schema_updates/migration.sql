/*
  Warnings:

  - You are about to drop the column `apply_link` on the `Tracked_Jobs` table. All the data in the column will be lost.
  - You are about to drop the column `companyId` on the `Tracked_Jobs` table. All the data in the column will be lost.
  - You are about to drop the column `experience` on the `Tracked_Jobs` table. All the data in the column will be lost.
  - You are about to drop the column `experience_max` on the `Tracked_Jobs` table. All the data in the column will be lost.
  - You are about to drop the column `experience_min` on the `Tracked_Jobs` table. All the data in the column will be lost.
  - You are about to drop the column `job_description` on the `Tracked_Jobs` table. All the data in the column will be lost.
  - You are about to drop the column `job_id` on the `Tracked_Jobs` table. All the data in the column will be lost.
  - You are about to drop the column `job_link` on the `Tracked_Jobs` table. All the data in the column will be lost.
  - You are about to drop the column `job_location` on the `Tracked_Jobs` table. All the data in the column will be lost.
  - You are about to drop the column `job_salary` on the `Tracked_Jobs` table. All the data in the column will be lost.
  - You are about to drop the column `job_type` on the `Tracked_Jobs` table. All the data in the column will be lost.
  - You are about to drop the column `posted` on the `Tracked_Jobs` table. All the data in the column will be lost.
  - You are about to drop the column `salary_max` on the `Tracked_Jobs` table. All the data in the column will be lost.
  - You are about to drop the column `salary_min` on the `Tracked_Jobs` table. All the data in the column will be lost.
  - You are about to drop the column `skills_required` on the `Tracked_Jobs` table. All the data in the column will be lost.
  - You are about to drop the column `source` on the `Tracked_Jobs` table. All the data in the column will be lost.
  - You are about to drop the column `source_logo` on the `Tracked_Jobs` table. All the data in the column will be lost.
  - You are about to drop the column `title` on the `Tracked_Jobs` table. All the data in the column will be lost.
  - The `status` column on the `Tracked_Jobs` table would be dropped and recreated. This will lead to data loss if there is data in the column.
  - You are about to drop the column `job_statuses` on the `User` table. All the data in the column will be lost.
  - You are about to drop the column `resume` on the `User` table. All the data in the column will be lost.
  - A unique constraint covering the columns `[title,job_id,companyId]` on the table `Job` will be added. If there are existing duplicate values, this will fail.
  - A unique constraint covering the columns `[jobId,userId]` on the table `Tracked_Jobs` will be added. If there are existing duplicate values, this will fail.
  - Added the required column `jobId` to the `Tracked_Jobs` table without a default value. This is not possible if the table is not empty.

*/
-- CreateEnum
CREATE TYPE "JobStatus" AS ENUM ('APPLIED', 'ACCEPTED', 'REJECTED');

-- DropForeignKey
ALTER TABLE "Tracked_Jobs" DROP CONSTRAINT "Tracked_Jobs_companyId_fkey";

-- DropIndex
DROP INDEX "UniqueJobTitleCompany";

-- DropIndex
DROP INDEX "Tracked_Jobs_job_id_key";

-- DropIndex
DROP INDEX "UniqueTrackedJob";

-- AlterTable
ALTER TABLE "Job" ADD COLUMN     "status" TEXT NOT NULL DEFAULT 'active';

-- AlterTable
ALTER TABLE "Tracked_Jobs" DROP COLUMN "apply_link",
DROP COLUMN "companyId",
DROP COLUMN "experience",
DROP COLUMN "experience_max",
DROP COLUMN "experience_min",
DROP COLUMN "job_description",
DROP COLUMN "job_id",
DROP COLUMN "job_link",
DROP COLUMN "job_location",
DROP COLUMN "job_salary",
DROP COLUMN "job_type",
DROP COLUMN "posted",
DROP COLUMN "salary_max",
DROP COLUMN "salary_min",
DROP COLUMN "skills_required",
DROP COLUMN "source",
DROP COLUMN "source_logo",
DROP COLUMN "title",
ADD COLUMN     "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN     "jobId" UUID NOT NULL,
ADD COLUMN     "resumeUrl" TEXT,
DROP COLUMN "status",
ADD COLUMN     "status" "JobStatus" NOT NULL DEFAULT 'APPLIED';

-- AlterTable
ALTER TABLE "User" DROP COLUMN "job_statuses",
DROP COLUMN "resume";

-- CreateTable
CREATE TABLE "ResumeSection" (
    "id" UUID NOT NULL,
    "userId" UUID NOT NULL,
    "sectionType" TEXT NOT NULL,
    "content" JSONB NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "ResumeSection_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "job_statuses" (
    "id" UUID NOT NULL,
    "userId" UUID NOT NULL,
    "label" TEXT NOT NULL,
    "value" INTEGER NOT NULL,

    CONSTRAINT "job_statuses_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "UniqueJobTitleCompany" ON "Job"("title", "job_id", "companyId");

-- CreateIndex
CREATE UNIQUE INDEX "UniqueTrackedJob" ON "Tracked_Jobs"("jobId", "userId");

-- AddForeignKey
ALTER TABLE "ResumeSection" ADD CONSTRAINT "ResumeSection_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "job_statuses" ADD CONSTRAINT "job_statuses_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Tracked_Jobs" ADD CONSTRAINT "Tracked_Jobs_jobId_fkey" FOREIGN KEY ("jobId") REFERENCES "Job"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
