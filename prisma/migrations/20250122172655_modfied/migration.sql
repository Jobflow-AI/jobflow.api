/*
  Warnings:

  - Made the column `title` on table `Tracked_Jobs` required. This step will fail if there are existing NULL values in that column.

*/
-- AlterTable
ALTER TABLE "Tracked_Jobs" ALTER COLUMN "title" SET NOT NULL,
ALTER COLUMN "title" DROP DEFAULT;
