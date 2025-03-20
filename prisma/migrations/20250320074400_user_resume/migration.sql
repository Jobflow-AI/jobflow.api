/*
  Warnings:

  - You are about to drop the column `resume_education` on the `User` table. All the data in the column will be lost.
  - You are about to drop the column `resume_experience` on the `User` table. All the data in the column will be lost.
  - You are about to drop the column `resume_links` on the `User` table. All the data in the column will be lost.
  - You are about to drop the column `resume_location` on the `User` table. All the data in the column will be lost.
  - You are about to drop the column `resume_phone` on the `User` table. All the data in the column will be lost.
  - You are about to drop the column `resume_projects` on the `User` table. All the data in the column will be lost.
  - You are about to drop the column `resume_skills` on the `User` table. All the data in the column will be lost.
  - You are about to drop the column `resume_summary` on the `User` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "User" DROP COLUMN "resume_education",
DROP COLUMN "resume_experience",
DROP COLUMN "resume_links",
DROP COLUMN "resume_location",
DROP COLUMN "resume_phone",
DROP COLUMN "resume_projects",
DROP COLUMN "resume_skills",
DROP COLUMN "resume_summary";
