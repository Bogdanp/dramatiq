-- requeue(args=[timestamp], keys=[queue_1, queue_2])
-- Requeues any unacked messages enqueues prior to $timestamp off of
-- all $KEYS.
local timestamp = ARGV[1]

local queue_name
local queue_acks
local message_ids
for i=1,#KEYS do
   queue_name = KEYS[i]
   queue_acks = queue_name .. ".acks"

   message_ids = redis.call("zrangebyscore", queue_acks, 0, timestamp)
   if next(message_ids) then
      redis.call("zrem", queue_acks, unpack(message_ids))
      redis.call("rpush", queue_name, unpack(message_ids))
   end
end
