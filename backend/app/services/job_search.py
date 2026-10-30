import asyncio
from .jobs import dedupe
from .job_sources.adzuna import AdzunaSource
from .job_sources.jsearch import JSearchSource
from .job_sources.jooble import JoobleSource
from .job_sources.ashby import AshbyBoardSource
from .job_sources.lever import LeverBoardSource
from .job_sources.greenhouse import GreenhouseBoardSource
from .job_sources.workable import WorkableSource
from .job_sources.smartrecruiters import SmartRecruitersSource
from .job_sources.career_sites import CareerSiteSource

class JobSearchService:
    def __init__(self, ashby_boards=None, lever_sites=None, greenhouse_boards=None, workable_accounts=None, smartrecruiters_companies=None, career_site_urls=None):
        self.sources = {
          "adzuna": AdzunaSource(),
          "jsearch": JSearchSource(),
          "jooble": JoobleSource(),
          "ashby": AshbyBoardSource(ashby_boards or []),
          "lever": LeverBoardSource(lever_sites or []),
          "greenhouse": GreenhouseBoardSource(greenhouse_boards or []),
          "workable": WorkableSource(workable_accounts or []),
          "smartrecruiters": SmartRecruitersSource(smartrecruiters_companies or []),
          "career_sites": CareerSiteSource(career_site_urls or [])
        }

    async def search(self, query, countries=None, remote_only=False, sources=None):
        names=sources or list(self.sources)
        tasks=[self.sources[n].search(query,countries or [],remote_only) for n in names if n in self.sources]
        results=await asyncio.gather(*tasks,return_exceptions=True)
        jobs=[]
        for r in results:
            if isinstance(r,list): jobs.extend(r)
        return dedupe(jobs)
