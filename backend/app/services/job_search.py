import asyncio
from .jobs import dedupe
from .employer_source_preflight import preflight_employer_source
from .job_sources.adzuna import AdzunaSource
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
        unique = dedupe(jobs)
        # Add evidence gate without altering existing search results or fit policy.
        # The ATS adapters must verify live forms and eligibility separately.
        for job in unique:
            job["employer_source_preflight"] = preflight_employer_source(job)
        return unique
