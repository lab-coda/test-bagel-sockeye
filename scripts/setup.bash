ALLOC=st-hwang240-1
WORK=/arc/project/$ALLOC/$USER/hbn-bagel
export APPTAINER_CACHEDIR=/scratch/$ALLOC/$USER/.apptainer_cache   # keep the cache out of $HOME
mkdir -p $WORK && cd $WORK

git clone git@github.com:lab-coda/recipes.git 
cp test-bagel-sockeye/template.env recipes/.env
cp test-bagel-sockeye/local_nb_nodes.template.json recipes/local_nb_nodes.json

mkdir -p sif state/graphdb_home state/data logs
apptainer pull sif/graphdb.sif docker://ontotext/graphdb:10.8.12
apptainer pull sif/api.sif     docker://neurobagel/api:latest
apptainer pull sif/fapi.sif    docker://neurobagel/federation_api:latest
apptainer pull sif/query.sif   docker://neurobagel/query_tool:latest

cd $WORK/recipes/init_data
python -m init_data.process_jsonld ../data ../state/data
cd ..