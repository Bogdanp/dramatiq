-- requeue(args=[timestamp], keys=[queue_1, queue_2])
-- Requeues any unacked messages enqueues prior to $timestamp off of
-- all $KEYS.
local timestamp = ARGV[1]

local queue_name
local queue_acks
local message_ids
local message_id
for i=1,#KEYS do
   queue_name = KEYS[i]
   queue_acks = queue_name .. ".acks"

   message_ids = redis.call("zrangebyscore", queue_acks, 0, timestamp)
   for j=1,#message_ids do
      message_id = message_ids[j]

      redis.call("zrem", queue_acks, message_id)
      redis.call("rpush", queue_name, message_id)
   end
end
