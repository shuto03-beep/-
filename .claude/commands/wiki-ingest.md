Read knowledge-base/CLAUDE.md for configuration. Then execute the Ingest operation:
1. Scan `knowledge-base/raw/` for files not yet referenced in `knowledge-base/wiki/sources/`
2. For each unprocessed file, create a source summary in `knowledge-base/wiki/sources/`
3. Extract and create/update concept pages in `knowledge-base/wiki/concepts/`
4. Extract and create/update entity pages in `knowledge-base/wiki/entities/`
5. Update `knowledge-base/wiki/index.md`
6. Append to `knowledge-base/wiki/log.md`
