-- Alert pressure by city for the Plano, Frisco and Dallas County book (synthetic), next to the real number of Dallas
-- County Clerk notice files posted for the same city (real, March to May sale months, file counts not notice counts).
with book as (
    select city, focus, count(*) as borrowers from {{ ref('dim_borrower') }} group by 1, 2
),
alerted as (
    select city, count(*) as alerted_borrowers, sum(case when hit then 1 else 0 end) as hits
    from {{ ref('fct_alert_outcomes') }} group by 1
),
real_files as (
    select city, sum(pdf_files) as dallas_county_notice_files from {{ source('ref', 'dallas_notice_files') }} group by 1
)
select b.city, b.focus, b.borrowers, coalesce(a.alerted_borrowers, 0) as alerted_borrowers,
       round(1000.0 * coalesce(a.alerted_borrowers, 0) / b.borrowers, 1) as alerts_per_1000_borrowers,
       r.dallas_county_notice_files
from book b
left join alerted a using (city)
left join real_files r using (city)
order by alerts_per_1000_borrowers desc
