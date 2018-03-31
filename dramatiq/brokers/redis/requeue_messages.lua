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
