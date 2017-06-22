-- nack(args=[queue_name, xqueue_name message_id])
-- This function removes a message from its queue's acks set and then
-- moves it to a different queue.
local queue_name = ARGV[1]
local xqueue_name = ARGV[2]
local message_id = ARGV[3]

local queue_acks = queue_name .. ".acks"
local queue_messages = queue_name .. ".msgs"
local xqueue_messages = xqueue_name .. ".msgs"

-- unack the message
redis.call("zrem", queue_acks, message_id)

-- then pop it off the messages hash
local message = redis.call("hget", queue_messages, message_id)
if message ~= nil then
   redis.call("hdel", queue_messages, message_id)
   redis.call("hset", xqueue_messages, message_id, message)
   redis.call("rpush", xqueue_name, message_id)
end
