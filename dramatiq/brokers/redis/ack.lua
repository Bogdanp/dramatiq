-- ack(args=[queue_name, message_id])
local queue_name = ARGV[1]
local message_id = ARGV[2]

local queue_acks = queue_name .. ".acks"
local queue_messages = queue_name .. ".msgs"

redis.call("lrem", queue_acks, 1, message_id)
redis.call("hdel", queue_messages, message_id)
