-- fetch(args=[queue_name, prefetch, timestamp])
-- This function fetches up to $prefetch number of messages for a
-- given queue.  All fetched messages are moved to the ack set.  The
-- timestamp is used to "score" each ack such that an external watcher
-- can efficiently move messages unacked some time prior to when it
-- runs back to their respective queues.
local queue_name = ARGV[1]
local prefetch = ARGV[2]
local timestamp = ARGV[3]

local queue_acks = queue_name .. ".acks"
local queue_messages = queue_name .. ".msgs"

local message_ids = {}
local message_id
for i=1,prefetch do
   message_id = redis.call("lpop", queue_name)
   if not message_id then
      break
   end

   message_ids[i] = message_id
   redis.call("zadd", queue_acks, timestamp, message_id)
end

if next(message_ids) == nil then
   return {}
else
   return redis.call("hmget", queue_messages, unpack(message_ids))
end
