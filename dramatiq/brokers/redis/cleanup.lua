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
