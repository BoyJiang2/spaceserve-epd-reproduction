> GitHub阅读副本：仅修正链接；[封存原文](../../../../outputs/epd-followup/source-event-excerpts.md) SHA256 9aa49f15a7fe04f3ddd722f0c6f5fa93686ad1c44dcc564a414e92cdd9eb469e。原数字及解释不变。

# Actual reconstructed source excerpts with original line numbers

Mechanically copied from the hash-listed source files; not a prose substitute for code.

## source/epdserve/orchestrator.py SHA256 6048f799c5e7c9a6838963e2e9ee3025f479793389375aaae8de815af5bced8e


```python
125:         self.request_outputs: Dict[int, asyncio.Queue[StepOutput]] = {}
126:         
127:         # request_id -> list of LifetimeEvent
128:         # self.request_lifetime_events: Dict[int, List[LifetimeEvent]] = {}
129:         self.request_lifetime_events = defaultdict(dict)
130:         self.engine_initialized = False
131:         # self.nvitop_devices = CudaDevice.all()
132:         self.load_estimator = LoadEstimator(self.encoding_cluster,
```


```python
195:         request_id: Optional[int],
196:         arrival_time: Optional[float] = None,
197:         **kwargs        
198:     ) -> AsyncGenerator[StepOutput, None]:
199:         """
200:         generate - Generate outputs for one request
201:         
202:         This function is intended to be used as an async generator, i.e., it can be
203:         used in a for loop. For example, `async for output in engine.generate(...)`
204:         """
205: 
206:         assert self.engine_initialized, "Engine not initialized. Please call engine.initialize() before generating."
207:         self._on_new_lifetime_event_callback(request_id, LifetimeEvent(LifetimeEventType.Issued))
208:         input['prompt_token_ids']  = self.tokenizer.encode(input['prompt'])
209:         model_input = self.input_processor(input)
210:         input['processed_prompt'] = model_input['prompt']
211:         input['processed_prompt_token_ids'] = model_input['prompt_token_ids']
212: 
213:         req = create_request(
214:             model_input=model_input,
215:             sampling_params=sampling_params,
216:             request_id=request_id,
217:             arrival_time=arrival_time if arrival_time is not None else time.perf_counter(),
218:             **kwargs              
219:         )
220: 
221:         self.request_outputs[req.request_id] = asyncio.Queue()
222:         self._on_new_lifetime_event_callback(req.request_id, LifetimeEvent(LifetimeEventType.Preprocessed))
223:         self.encoding_cluster.add_request(req)
224:         
225:         while True:
```

## source/epdserve/engine_encoding.py SHA256 fcdc6809e79e4b567f02fe7f6724ccc105ef2c8af5eba5ba3055ff9d1e126644


```python
310:                 if isinstance(request.request_id, str): # Handle the IRP case
311:                     # TODO: fix this to make sure that it should take a max of all shards.
312:                     unsharded_req_id, sharded_req_idx, sharded_total_reqs = [int(val) for val in request.request_id.split('_')]
313:                     request_id = unsharded_req_id
314:                 else:
315:                     request_id = request.request_id
316:                 self.engine_on_new_lifetime_event_callback(
317:                     request_id,
318:                     LifetimeEvent(LifetimeEventType.EncodingBegin)
319:                 )
320:                 
321:             # push the batch into pipeline
322:             batched_requests.start_one_iteration(time.perf_counter())
323:             self.batches_in_pipeline.append(batched_requests)
324: 
325:             block_tables = self.vision_block_manager.get_partial_block_table(batched_requests.get_request_ids())
326:             remote_calls = self._remote_call_all_workers_async(
327:                 "step_encoding",
```


```python
350:                 finished_batch = self.batches_in_pipeline[0]
351:                 finished_batch.finish_one_iteration(None, None, end_time)
352:                 
353:                 self.scheduler.on_finish_requests(finished_batch)
354:                 
355:                 for request in finished_batch.requests:
356:                     if isinstance(request.request_id, str): # Handle the IRP case
357:                         # TODO: fix this to make sure that it should take a max of all shards.
358:                         unsharded_req_id, sharded_req_idx, sharded_total_reqs = [int(val) for val in request.request_id.split('_')]
359:                         request_id = unsharded_req_id
360:                     else:
361:                         request_id = request.request_id
362:                     self.engine_on_new_lifetime_event_callback(
363:                         request_id,
364:                         LifetimeEvent(LifetimeEventType.EncodingEnd)
365:                     )
366:                 # Cannot free blocks now! The decoding stage may still need them!
367: 
368:                 self.batches_in_pipeline.pop(0)
369:                 self.batches_ret_futures.pop(0)
370:                 
371:                 # Inform the user that the request has finished the context stage
372:                 for request in finished_batch.requests:
373:                     if not request.is_finished:
374:                         # Push the request into the bridge queue if it is not finished
```

## source/epdserve/engine_context.py SHA256 f6d40aa24f3fe3d17761524f2e2fe7ee1c7d6612c14fb1a48227fb10006ed343


```python
262:             # 2. No enough free blocks (e.g. the decoding stage is too slow)
263:             self.batches_in_pipeline.append(batched_requests)
264:             self.batches_ret_futures.append(None)
265:             await asyncio.sleep(SLEEP_WHEN_CONTEXT_NO_REQUEST)
266:         else:
267:             self.block_manager.allocate_blocks_batched(batched_requests)
268:             
269:             # Log down the lifetime event
270:             for request in batched_requests.requests:
271:                 self.engine_on_new_lifetime_event_callback(request.request_id,
272:                                                            LifetimeEvent(LifetimeEventType.ContextBegin))
273:                 
274:             # push the batch into pipeline
275:             batched_requests.start_one_iteration(time.perf_counter())
276:             self.batches_in_pipeline.append(batched_requests)
277: 
278: 
279:             block_tables_all = self.block_manager.get_partial_block_table(batched_requests.get_request_ids())
```


```python
329:                 self.scheduler.on_finish_requests(finished_batch)
330:                 
331:                 for request, new_token, new_token_id in zip(
332:                     finished_batch.requests, generated_tokens, generated_tokens_ids
333:                 ):
334:                     step_output = StepOutput(request, new_token, new_token_id)
335:                     self.engine_on_new_lifetime_event_callback(
336:                         request.request_id,
337:                         LifetimeEvent(LifetimeEventType.ContextEnd)
338:                     )
339:                     self.engine_on_new_step_output_callback(
340:                         request.request_id,
341:                         step_output
342:                     )
343: 
344:                 # Cannot free blocks now! The decoding stage may still need them!
345: 
346:                 self.batches_in_pipeline.pop(0)
347:                 self.batches_ret_futures.pop(0)
348:                 
349:                 # Inform the user that the request has finished the context stage
350:                 for request in finished_batch.requests:
351:                     if not request.is_finished:
352:                         # Push the request into the bridge queue if it is not finished
353:                         migrating_req = MigratingRequest(
354:                             req=request,
355:                             block_indexes=self.block_manager.get_block_table(request.request_id),
```


```python
372: 
373:         if isinstance(migrating_req.req.request_id, str): # Handle the IRP case
374:             # TODO: fix this to make sure that it should take a max of all shards.
375:             unsharded_req_id, sharded_req_idx, sharded_total_reqs = [int(val) for val in migrating_req.req.request_id.split('_')]
376:             request_id = unsharded_req_id
377:         else:
378:             request_id = migrating_req.req.request_id
379: 
380:         self.engine_on_new_lifetime_event_callback(
381:             request_id,
382:             LifetimeEvent(LifetimeEventType.EncodingMigrationBegin)
383:         )
384:         
385:         await asyncio.wait(self._remote_call_all_workers_async(
386:             "migrate_blocks_encoding",
387:             migrating_req.block_indexes, # encoding block indices
388:             migrating_req.source_parallel_config,
389:             target_block_indexes # context block indices
390:         ))
391:         self.engine_on_new_lifetime_event_callback(
392:             request_id,
393:             LifetimeEvent(LifetimeEventType.EncodingMigrationEnd)
394:         )
395:     
396:         # Clear the blocks on the encoding engine's side
397:         self.clear_migrated_blocks_callback_encoding(migrating_req)
398: 
399:             
```

## source/epdserve/engine_decoding.py SHA256 65d8f1d045af8608ea368232d67841572a037f064651b2708b7772cdf64214af


```python
245:         # Here we temporarily backup the generated tokens and generated token ids
246:         # since we are going to overwrite them later when allocating blocks
247:         generated_token_bkup = migrating_req.req.generated_tokens
248:         generated_token_ids_bkup = migrating_req.req.generated_token_ids
249:         migrating_req.req.generated_tokens = []
250:         migrating_req.req.generated_token_ids = []
251:         self.block_manager.allocate_blocks(migrating_req.req)
252:         migrating_req.req.generated_tokens = generated_token_bkup
253:         migrating_req.req.generated_token_ids = generated_token_ids_bkup
254:         
255:         target_block_indexes = self.block_manager.get_block_table(migrating_req.req.request_id)
256:         assert len(target_block_indexes) == len(migrating_req.block_indexes)
257:         
258:         # Transfer the blocks
259:         self.engine_on_new_lifetime_event_callback(
260:             migrating_req.req.request_id,
261:             LifetimeEvent(LifetimeEventType.MigrationBegin)
262:         )
263:         await asyncio.wait(self._remote_call_all_workers_async(
264:             "migrate_blocks_context",
265:             migrating_req.block_indexes,
266:             migrating_req.source_parallel_config,
267:             target_block_indexes
268:         ))
269:         self.engine_on_new_lifetime_event_callback(
270:             migrating_req.req.request_id,
271:             LifetimeEvent(LifetimeEventType.MigrationEnd)
272:         )
273:     
274:         # Clear the blocks on the context engine's side
275:         await self.clear_migrated_blocks_callback_context(migrating_req)
276:             
277: 
```


```python
298:         else:
299:             # logger.info(colored(f"Decoding batch of length {len(batched_requests.requests)}", 'green'))
300:             # start_time = time.perf_counter()
301:             # Log down the lifetime event
302: 
303:             for request in batched_requests.requests:
304:                 self.engine_on_new_lifetime_event_callback(
305:                     request.request_id,
306:                     LifetimeEvent(LifetimeEventType.DecodingBegin),
307:                     True
308:                 )
309: 
310:             # Allocate blocks as needed
311:             self.block_manager.allocate_blocks_batched(batched_requests)
312: 
313:             # Check if all requests are on GPU (i.e. not swapped out)
```

## source/epdserve/api_server.py SHA256 2893de76c34708d17e5be23219c49919bc6459ebbb6c703f88d98d73b8b79659


```python
136:                                         arrival_time=arrival_time,
137:                                         enable_irp=bool(args.intra_request_dp))
138: 
139:     final_outputs: List[Tuple[StepOutput, float]] = [] # (step_output, timestamp)
140:     async for step_output in results_generator:
141:         if await request.is_disconnected():
142:             # Abort the request if the client disconnects.
143:             await engine.abort(request_id)
144:             return Response(status_code=499)
145:         final_outputs.append((step_output, time.perf_counter()))
146: 
147:     request_events = engine.get_and_pop_request_lifetime_events(request_id)
148:     
149:     text_output = prompt + ''.join([step_output[0].new_token for step_output in final_outputs])
150:     ret = {
151:         # "text": text_output,
152:         "prompt": prompt,
153:         "output": ''.join([step_output[0].new_token for step_output in final_outputs]),
154:         'output_token_ids': [step_output[0].new_token_id for step_output in final_outputs],
155:         'processed_prompt_token_ids': input_dict['processed_prompt_token_ids'],
156:         'prompt_token_len': len(input_dict['prompt_token_ids']),
157:         'processed_prompt_token_len': len(input_dict['processed_prompt_token_ids']),
158:         "timestamps": [step_output[1] for step_output in final_outputs],
159:         "lifetime_events": json_encode_lifetime_events(request_events.values())
160:     }
161:     return JSONResponse(ret)
```