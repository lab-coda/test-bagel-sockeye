# on the compute node:
ALLOC=st-hwang240-1
WORK=/arc/project/$ALLOC/$USER/hbn-bagel

cd $WORK/recipes
module load apptainer 2>/dev/null || true
set -a; source .env; set +a
SECRETS="-B secrets/NB_GRAPH_ADMIN_PASSWORD.txt:/run/secrets/db_admin_password \
         -B secrets/NB_GRAPH_PASSWORD.txt:/run/secrets/db_user_password"

# GraphDB + setup.sh (creates the repo and uploads the example data)
apptainer exec --cleanenv --writable-tmpfs $SECRETS \
  -B state/graphdb_home:/opt/graphdb/home \
  -B scripts:/usr/src/neurobagel/scripts \
  -B vocab:/usr/src/neurobagel/vocab \
  -B state/data:/data \
  --pwd /usr/src/neurobagel/scripts \
  --env NB_GRAPH_USERNAME=$NB_GRAPH_USERNAME,NB_GRAPH_PORT=7200,NB_GRAPH_DB=${NB_GRAPH_DB:-repositories/my_db},NB_GRAPH_MEMORY=4G \
  sif/graphdb.sif ./setup.sh > logs/graph.log 2>&1 &

# wait until setup.sh reports the upload is done
tail -f logs/graph.log    # Ctrl-C once it's done

# Node API
apptainer exec --cleanenv $SECRETS \
  -B scripts/api_entrypoint.sh:/usr/src/api_entrypoint.sh \
  -B state/data:/data \
  --env NB_GRAPH_USERNAME=$NB_GRAPH_USERNAME,NB_GRAPH_ADDRESS=localhost,NB_GRAPH_PORT=7200,NB_GRAPH_DB=${NB_GRAPH_DB:-repositories/my_db},NB_DATASETS_METADATA_PATH=/data/datasets_metadata.json,NB_RETURN_AGG=true,NB_MIN_CELL_SIZE=0,NB_API_PORT=8000,NB_ENABLE_AUTH=false,NB_CONFIG=Neurobagel,NB_CATALOG_MODE=false \
  sif/api.sif /usr/src/api_entrypoint.sh > logs/api.log 2>&1 &

# Federation API on 8080 (the image listens on 8000 internally, so override the port)
apptainer run --cleanenv \
  -B local_nb_nodes.json:/usr/src/local_nb_nodes.json \
  --env NB_API_PORT=8080,NB_FEDERATE_REMOTE_PUBLIC_NODES=${NB_FEDERATE_REMOTE_PUBLIC_NODES:-False},NB_ENABLE_AUTH=false \
  sif/fapi.sif > logs/fapi.log 2>&1 &

# Query tool (Vite dev server on 5173)
apptainer run --cleanenv --writable-tmpfs \
  --env NB_API_QUERY_URL=http://localhost:8080,NB_QUERY_APP_BASE_PATH=/,NB_ENABLE_AUTH=false \
  sif/query.sif > logs/query.log 2>&1 &

hostname   # note this, e.g. se123
