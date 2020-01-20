-- This file is a part of Dramatiq.
--
-- Copyright (C) 2020 CLEARTYPE SRL <bogdan@cleartype.io>
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

local function unpack_with_size(n)
    local items = {}
    for i = 0, n do
        items[i] = 0
    end

    (table.unpack or unpack)(items)
end

-- Programmers tend to pick multiples of 2 for their limits.  Assuming
-- that whomever sets LUAI_MAXCSTACK picks a value over 1024, starting
-- from 999 will let us find a close-enough value to the limit in very
-- few steps.
local function find_max_unpack_size()
    local size = 999
    while true do
        if pcall(function() unpack_with_size(size * 2) end) then
            size = size * 2
        else
            return size
        end
    end
end

return find_max_unpack_size()
