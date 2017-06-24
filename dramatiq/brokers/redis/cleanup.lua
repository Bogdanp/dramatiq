-- cleanup(args=[timestamp], keys=[queue_1, queue_2])
-- Drops any dead-lettered messages older than $timestamp.
local timestamp = ARGV[1]

local queue_name
local queue_messages
local message_ids
local message_id
for i=1,#KEYS do
   queue_name = KEYS[i]
   queue_messages = queue_name .. ".msgs"

   message_ids = redis.call("zrangebyscore", queue_name, 0, timestamp)
   for j=1,#message_ids do
      message_id = message_ids[j]

      redis.call("zrem", queue_name, message_id)
      redis.call("hdel", queue_messages, message_id)
   end
end
