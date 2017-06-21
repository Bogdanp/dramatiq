-- enqueue(args=[queue_name, message_id, message_data])
local queue_name = ARGV[1]
local message_id = ARGV[2]
local message_data = ARGV[3]

local queue_messages = queue_name .. ".msgs"

redis.call("hset", queue_messages, message_id, message_data)
redis.call("lpush", queue_name, message_id)
