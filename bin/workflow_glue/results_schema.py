# generated by datamodel-codegen:
#   filename:  results_schema.yml

from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional

from pydantic import Field

from workflow_glue.results_schema_helpers import BaseModel


class SampleType(str, Enum):
    """
    The type of the sample
    """

    no_template_control = 'no_template_control'
    positive_control = 'positive_control'
    negative_control = 'negative_control'
    test_sample = 'test_sample'


class FastqStats(BaseModel):
    """
    A place to store read statistics
    """

    n_seqs: Optional[int] = Field(None, description='The number of sequencing reads')
    n_bases: Optional[int] = Field(None, description='The number of bases')
    min_length: Optional[int] = Field(None, description='The minimum read length')
    max_length: Optional[int] = Field(None, description='The maximum read length')
    mean_quality: Optional[float] = Field(None, description='The mean read quality')


class AMRVariants(BaseModel):
    """
    AMR associated variant information
    """

    gene: Optional[str] = None
    database: Optional[str] = None
    drugs: Optional[List] = Field(
        None, description='Antimicrobials affected by variant'
    )
    aa: Optional[str] = Field(None, description='Amino acid mutation')
    nuc: Optional[str] = Field(None, description='nucleotide mutation')
    coverage: Optional[Any] = None
    identity: Optional[Any] = None
    start: Optional[int] = None
    end: Optional[int] = None
    contig: Optional[str] = None
    pmids: Optional[str] = Field(
        None, description='PMID or accession number for reference paper'
    )


class SequenceTypeSchema(BaseModel):
    """
    MLST schema and allele variant identified for sample
    """

    schema_identifier: Optional[str] = None
    allele_variant: Optional[str] = None


class Serotype(BaseModel):
    """
    Salmonella serotyping results
    """

    predicted_serotype: Optional[str] = None
    predicted_antigenic_profile: Optional[str] = None
    o_antigen_prediction: Optional[str] = None
    h1_antigen_prediction: Optional[str] = None
    h2_antigen_prediction: Optional[str] = None
    qc_status: Optional[str] = None


class Annotation(BaseModel):
    """
    Region of interest identified within assembly
    """

    contig: Optional[str] = None
    ID: Optional[str] = None
    start: Optional[int] = None
    end: Optional[int] = None
    strand: Optional[str] = None
    gene: Optional[str] = None
    product: Optional[str] = None
    ec_number: Optional[str] = Field(
        None, description='Identifier from the enzyme consortium catalogue'
    )


class Variant(BaseModel):
    """
    Variants identified in assembly compared to reference
    """

    contig: Optional[str] = None
    pos: Optional[int] = None
    ref: Optional[str] = None
    alt: Optional[str] = None
    depth: Optional[int] = None


class Coverage(BaseModel):
    """
    Coverage summary information for each contig in assembly
    """

    counts: Optional[int] = None
    median: Optional[float] = Field(None, description='Median coverage')
    mean: Optional[float] = Field(None, description='Mean coverage')
    minimum: Optional[int] = Field(None, description='Minimum coverage')
    maximum: Optional[int] = Field(None, description='Maximum coverage')


class AntimicrobialResistance(BaseModel):
    """
    The antimicrobial resistance results for the sample
    """

    detected_variants: Optional[List[AMRVariants]] = None


class MLST(BaseModel):
    """
    Multi-locus sequence typing results for the sample
    """

    detected_species: Optional[str] = None
    sequence_type: Optional[str] = None
    typing_schema: Optional[List[SequenceTypeSchema]] = None


class Contig(BaseModel):
    """
    Summary statistics for contig in assembly
    """

    name: Optional[str] = None
    length: Optional[int] = None
    coverage: Optional[Coverage] = None


class Assembly(BaseModel):
    """
    Draft genome assembly statistics of the sample
    """

    reference: Optional[str] = Field(
        None,
        description='Name of the reference used in the assembly process. Null for de-novo',
    )
    annotations: Optional[List[Annotation]] = Field(
        None, description='Array of regions of interest identified within the assembly'
    )
    variants: Optional[List[Variant]] = None
    contig: Optional[List[Contig]] = None


class ResultsContents(BaseModel):
    antimicrobial_resistance: Optional[AntimicrobialResistance] = None
    assembly: Optional[Assembly] = None
    sequence_typing: Optional[MLST] = None
    serotyping: Optional[Serotype] = None
    fastq: Optional[FastqStats] = None


class Sample(BaseModel):
    """
    A sample sheet entry and its corresponding checks and related results
    """

    alias: str = Field(..., description='The alias for the sample given by the user')
    barcode: str = Field(..., description='The physical barcode assigned to the sample')
    sample_type: SampleType = Field(..., description='The type of the sample')
    results: ResultsContents = Field(
        ..., description='Further specific workflow results for this sample'
    )


class WorkflowResult(BaseModel):
    """
    Definition for results that will be returned by this workflow. This structure will be passed through by Gizmo speaking clients as WorkflowInstance.results.
    """

    samples: List[Sample] = Field(..., description='Samples in this workflow instance')
