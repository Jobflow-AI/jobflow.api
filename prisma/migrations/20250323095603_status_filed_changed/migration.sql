/*
  Warnings:

  - The `status` column on the `Tracked_Jobs` table would be dropped and recreated. This will lead to data loss if there is data in the column.

*/
-- AlterEnum
ALTER TYPE "JobStatus" ADD VALUE 'BOOKMARKED';

-- AlterTable
ALTER TABLE "Tracked_Jobs" DROP COLUMN "status",
ADD COLUMN     "status" TEXT NOT NULL DEFAULT 'APPLIED';
