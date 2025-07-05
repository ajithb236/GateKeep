#custom async LRU cache implementation with TTL(Time to Live) support
import asyncio
import time
ttl= 60000 # Default TTL in seconds (10 minutes)
#Doubly Linked List for LRU cache
class Node:
    def __init__(self, key, value, ttl_seconds):
        self.key = key
        self.value = value
        self.expires_at = time.time() + ttl_seconds 
        self.prev = None
        self.next = None

class AsyncLRUCache:
    def __init__(self, maxsize=1000, ttlseconds=ttl):
        self.cache = {}  #each ele is a DLL node
        self.maxsize = maxsize
        self.lock = asyncio.Lock()
        self.ttl = ttlseconds
        # Dummy head and tail for simplicity
        self.head = Node(None, None,self.ttl)
        self.tail = Node(None, None,self.ttl)
        self.head.next = self.tail
        self.tail.prev = self.head
        self.cleanup_task = asyncio.create_task(self.cleanup())
    def remove_node(self, node):
        prev, nxt = node.prev, node.next
        prev.next = nxt
        nxt.prev = prev

    def add_to_tail(self, node):
        prev = self.tail.prev
        prev.next = node
        node.prev = prev
        node.next = self.tail
        self.tail.prev = node

    async def get(self, key):
        async with self.lock:
            node = self.cache.get(key)
            if not node:
                return None

            # Check TTL
            if node.expires_at and time.time() > node.expires_at:
                self.remove_node(node)
                del self.cache[key]
                return None

            # Mark as recently used
            self.remove_node(node)
            self.add_to_tail(node)
            return node.value

    async def set(self, key, value):
        async with self.lock:
            if key in self.cache:
                node = self.cache[key]
                node.value = value
                node.expires_at = time.time() + self.ttl
                self.remove_node(node)
                self.add_to_tail(node)
            else:
                if len(self.cache) >= self.maxsize:
   
                    lru = self.head.next
                    self.remove_node(lru)
                    del self.cache[lru.key]
                new_node = Node(key, value, self.ttl)
                self.cache[key] = new_node
                self.add_to_tail(new_node)
    async def cleanup(self):
        while True:
            await asyncio.sleep(70)  # cleanup every 70s
            async with self.lock:
                current = self.head.next
                while current != self.tail:
                    if current.expires_at and time.time() > current.expires_at:
                        self.remove_node(current)
                        del self.cache[current.key]
                    current = current.next
