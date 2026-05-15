local msg = redis.call('ZRANGEBYSCORE', KEYS[1], 0, ARGV[1], 'LIMIT', 0, 1)
if #msg > 0 then
    redis.call('ZREM', KEYS[1], msg[1])
    redis.call('LPUSH', KEYS[2], msg[1])
    return msg[1]
end
return nil
