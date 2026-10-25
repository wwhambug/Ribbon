import { sqliteTable, text, integer, index } from 'drizzle-orm/sqlite-core';

export const chats = sqliteTable('chats', {
  id: text('id').primaryKey(),
  title: text('title').notNull(),
  created: integer('created').notNull(),
  remoteCreated: integer('remote_created').notNull().default(0),
});
export const jobs = sqliteTable('jobs', {
  id: text('id').primaryKey(),
  chatId: text('chat_id').notNull().references(() => chats.id),
  message: text('message').notNull(),
  status: text('status').notNull(),
  created: integer('created').notNull(),
  updated: integer('updated').notNull(),
  lease: text('lease'),
  leaseUntil: integer('lease_until'),
  remoteAck: integer('remote_ack').notNull().default(0),
  error: text('error'),
}, table => [index('jobs_status_created_idx').on(table.status, table.created),
             index('jobs_chat_idx').on(table.chatId, table.created)]);
export const events = sqliteTable('events', {
  seq: integer('seq').primaryKey({ autoIncrement: true }),
  jobId: text('job_id').notNull().references(() => jobs.id),
  kind: text('kind').notNull(),
  payload: text('payload').notNull(),
  created: integer('created').notNull(),
}, table => [index('events_job_idx').on(table.jobId, table.seq)]);
export const runner = sqliteTable('runner', {
  id: text('id').primaryKey(),
  seen: integer('seen').notNull(),
  location: text('location').notNull(),
});
