-- This file is a part of Dramatiq.
--
-- Copyright (C) 2017,2018 CLEARTYPE SRL <bogdan@cleartype.io>
--
-- Dramatiq is free software; you can redistribute it and/or modify it
-- under the terms of the GNU Lesser General Public License as published by
-- the Free Software Foundation, either version 3 of the License, or (at
-- your option) any later version.
--
-- Dramatiq is distributed in the hope that it will be useful, but WITHOUT
-- ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
-- FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
-- License for more details.
--
-- You should have received a copy of the GNU Lesser General Public License
-- along with this program.  If not, see <http://www.gnu.org/licenses/>.

-- enqueue(args=[queue_name, message_id, message_data])
-- This function stores a message in Redis and appends its id to a list.
--
-- ${queue_name} is a Redis list of message ids [message_1, message_2, message_3]
-- ${queue_name}.msgs is a hash of message ids to message payloads
-- ${queue_name}.acks is a zset of message ids scored by the timestamp
-- each message was pulled off the queue.
local queue_name = ARGV[1]
local message_id = ARGV[2]
local message_data = ARGV[3]

local queue_messages = queue_name .. ".msgs"

redis.call("hset", queue_messages, message_id, message_data)
redis.call("rpush", queue_name, message_id)
