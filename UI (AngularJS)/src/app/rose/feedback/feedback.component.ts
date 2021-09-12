import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ResourceService } from 'src/app/services/resource.service';

@Component({
  selector: 'app-feedback',
  templateUrl: './feedback.component.html',
  styleUrls: ['./feedback.component.scss']
})
export class FeedbackComponent implements OnInit {

  private plantId = "";
  public activeFeed: boolean = false;
  public humidity: number = 0;
  public illum: number = 0;
  public light: number = 0;
  private isAuto: boolean = false;
  private isManual: boolean = false;

  constructor(private router: Router, private  resourceService: ResourceService, private activeRoute: ActivatedRoute) { }

  ngOnInit(): void {
    this.activeRoute.queryParamMap.subscribe(paramMap => {
      this.activeFeed = paramMap.get("feedback")==="true";
    })

    this.plantId = this.router.url.split('/')[1].split(';')[0];

    this.getSchedule();
    this.getPlantStatus();
  }

  private getPlantStatus() {
    this.resourceService.getPlantStatus(this.plantId).subscribe(
      (data) => {
        if (data.includes('auto')) {
          this.isAuto = true;
        }
        if (data.includes('manual')) {
          this.isManual = true;
        }
      },
      error => {
        console.log(error);
      }
    );
  }

  public changeStatus() {
    if (this.activeFeed) {
      this.resourceService.setPlantStatusFeedbackDisable(this.plantId).subscribe(
        (data) => {
          this.activeFeed = false
          document.getElementById('feedbackId')?.classList.remove('active')

          this.router.navigate(['.'],
          {
            relativeTo: this.activeRoute,
            queryParams: { feedback: false },
            queryParamsHandling: 'merge'
          })
        },
        error => {
          console.log(error);
        }
      )
    } else {
      if (!this.isAuto && !this.isManual) {
        let feedback = {
          light_time: this.light,
          hum_thresh: this.humidity,
          illum_thresh: this.illum
        }

        this.resourceService.setPlantStatusFeedbackEnable(this.plantId, JSON.stringify(feedback)).subscribe(
          (data) => {
            this.activeFeed = true
            document.getElementById('feedbackId')?.classList.add('active')

            this.router.navigate(['.'],
            {
              relativeTo: this.activeRoute,
              queryParams: { feedback: true },
              queryParamsHandling: 'merge'
            })
          },
          error => {
            if (error.status === 500) {
              this.activeFeed = true
              document.getElementById('feedbackId')?.classList.add('active')

              this.router.navigate(['.'],
              {
                relativeTo: this.activeRoute,
                queryParams: { feedback: true },
                queryParamsHandling: 'merge'
              })
            }
            console.log(error);
          }
        )
      } else {
      document.getElementById("errButton")?.click();
      (<HTMLInputElement>document.getElementById("customSwitch3")).checked = false;
      }
    }
  }

  public setSchedule() {
    let feedback = {
      light_time: this.light,
      hum_thresh: this.humidity,
      illum_thresh: this.illum
    }
    console.log(JSON.stringify(feedback));

    this.resourceService.setFeedbackParams(this.plantId, JSON.stringify(feedback)).subscribe(
      (data) => {
        console.log(data);
      },
      error => console.log(error)
    );


  }



  private getSchedule() {
    this.resourceService.getFeedbackParams(this.plantId).subscribe(
      data => {
        if (data !== null) {
          let x = JSON.parse(JSON.stringify(data))
          this.light = x["light_time"];
          this.humidity = x["hum_thresh"];
          this.illum = x["illum_thresh"];
        }
      },
      error => console.log(error)
    );
  }

}
