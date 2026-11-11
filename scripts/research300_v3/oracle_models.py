"""Only the maintainer uses the frozen, already qualified representations."""
from scripts.research300_v3.support import V2,load
canonical=load('v3_oracle_representations',V2/'oracle_models.py').canonical
