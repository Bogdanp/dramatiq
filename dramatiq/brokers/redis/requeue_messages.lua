-- requeue_messages(args=[queue_name], keys=[message_id_1, message_id_2])
-- Requeues a list of unacked messages.
local queue_name = ARGV[1]

local queue_acks = queue_name .. ".acks"
local queue_messages = queue_name .. ".msgs"

local message_id
for i=1,#KEYS do
   message_id = KEYS[i]

   redis.call("zrem", queue_acks, message_id)
   if redis.call("hexists", queue_messages, message_id) then
      redis.call("rpush", queue_name, message_id)
   end
end
