ALLOC=st-hwang240-1
WORK=/scratch/$ALLOC/$USER/neurobagel
export APPTAINER_CACHEDIR=/scratch/$ALLOC/$USER/.apptainer_cache   # keep the cache out of $HOME
mkdir -p $WORK && cd $WORK

cd /arc/project/$ALLOC/$USER

git clone git@github.com:lab-coda/recipes.git && cd recipes
cp template.env .env
cp local_nb_nodes.template.json local_nb_nodes.json

mkdir -p sif state/graphdb_home state/data logs
apptainer pull sif/graphdb.sif docker://ontotext/graphdb:10.8.12
apptainer pull sif/api.sif     docker://neurobagel/api:latest
apptainer pull sif/fapi.sif    docker://neurobagel/federation_api:latest
apptainer pull sif/query.sif   docker://neurobagel/query_tool:latest